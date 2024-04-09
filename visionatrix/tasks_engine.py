import asyncio
import builtins
import contextlib
import gc
import json
import logging
import os
import time
import typing
from datetime import datetime

import httpx
from sqlalchemy import and_, delete, update
from sqlalchemy.exc import IntegrityError

from . import database, options
from .comfyui import cleanup_models, interrupt_processing, soft_empty_cache
from .flows import get_installed_flows_names

LOGGER = logging.getLogger("visionatrix")

ACTIVE_TASK: dict = {}


def create_new_task(name: str, input_params: dict, user_info: database.UserInfo) -> dict:
    session = database.SESSION()
    try:
        new_task_queue = database.TaskQueue()
        session.add(new_task_queue)
        session.commit()
        remove_task_files(new_task_queue.id, ["output", "input"])
        return {
            "task_id": new_task_queue.id,
            "name": name,
            "input_params": input_params,
            "progress": 0.0,
            "error": "",
            "outputs": [],
            "input_files": [],
            "flow_comfy": {},
            "user_id": user_info.user_id,
        }
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to add `%s` to TaskQueue(%s)", name, user_info.user_id)
        raise
    finally:
        session.close()


def put_task_in_queue(task_details: dict) -> None:
    LOGGER.debug("Put flow in queue: %s", task_details)
    session = database.SESSION()
    try:
        new_task = database.TaskDetails(
            task_id=task_details["task_id"],
            name=task_details["name"],
            input_params=task_details["input_params"],
            progress=task_details["progress"],
            error=task_details["error"],
            outputs=task_details["outputs"],
            input_files=task_details["input_files"],
            flow_comfy=task_details["flow_comfy"],
            user_id=task_details["user_id"],
        )
        session.add(new_task)
        session.commit()
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to put task in queue: %s", task_details["task_id"])
        remove_task_files(task_details["task_id"], ["input"])
        raise
    finally:
        session.close()


def get_task(task_id: int, user_id: str | None = None) -> dict | None:
    session = database.SESSION()
    try:
        query = session.query(database.TaskDetails).filter(database.TaskDetails.task_id == task_id)
        if user_id is not None:
            query = query.filter(database.TaskDetails.user_id == user_id)
        task = query.first()
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "progress": task.progress,
            "error": task.error,
            "name": task.name,
            "input_params": task.input_params,
            "outputs": task.outputs,
            "input_files": task.input_files,
            "flow_comfy": task.flow_comfy,
            "user_id": task.user_id,
        }
    except Exception:
        LOGGER.exception("Failed to retrieve task: %s", task_id)
        raise
    finally:
        session.close()


def get_incomplete_task_without_error(tasks_to_ask: list[str]) -> dict:
    if options.VIX_MODE == "WORKER" and options.VIX_HOST:
        return get_incomplete_task_without_error_server(tasks_to_ask)
    return get_incomplete_task_without_error_database(tasks_to_ask)


def get_incomplete_task_without_error_server(tasks_to_ask: list[str]) -> dict:
    try:
        r = httpx.post(
            options.VIX_HOST.rstrip("/") + "/task-worker/get", data={"tasks_names": tasks_to_ask}, auth=__worker_auth()
        )
        if not httpx.codes.is_error(r.status_code):
            return json.loads(r.text)["task"]
        LOGGER.error("Server return status: %s", r.status_code)
    except Exception as e:
        LOGGER.exception("Connect exception occurred")
        if isinstance(e, httpx.ConnectError):
            time.sleep(5)
    return {}


def get_incomplete_task_without_error_database(tasks_to_ask: list[str], user_id: str | None = None) -> dict:
    if not tasks_to_ask:
        return {}
    session = database.SESSION()
    try:
        query = session.query(database.TaskDetails).outerjoin(
            database.TaskLock, database.TaskDetails.task_id == database.TaskLock.task_id
        )
        query = query.filter(
            database.TaskDetails.error == "",
            database.TaskDetails.progress != 100.0,
            database.TaskLock.id.is_(None),
            database.TaskDetails.name.in_(tasks_to_ask),
        )
        if user_id is not None:
            query = query.filter(database.TaskDetails.user_id == user_id)
        task = query.first()
        if not task:
            return {}
        try:
            lock = database.TaskLock(task_id=task.task_id, locked_at=datetime.utcnow())
            session.add(lock)
            session.commit()
        except IntegrityError:
            session.rollback()
            return {}
        return {
            "task_id": task.task_id,
            "progress": 0.0,
            "error": task.error,
            "name": task.name,
            "input_params": task.input_params,
            "outputs": task.outputs,
            "input_files": task.input_files,
            "flow_comfy": task.flow_comfy,
            "user_id": task.user_id,
        }
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to retrieve task for processing: %s", e)
        return {}
    finally:
        session.close()


def get_tasks(name: str | None = None, finished: bool | None = None, user_id: str | None = None) -> dict:
    session = database.SESSION()
    try:
        query = session.query(database.TaskDetails)
        if user_id is not None:
            query = query.filter(database.TaskDetails.user_id == user_id)
        if name is not None:
            query = query.filter(database.TaskDetails.name == name)
        if finished is not None:
            if finished:
                query = query.filter(database.TaskDetails.progress == 100.0)
            else:
                query = query.filter(database.TaskDetails.progress < 100.0)
        tasks = query.all()
        return {
            task.task_id: {
                "task_id": task.task_id,
                "progress": task.progress,
                "error": task.error,
                "name": task.name,
                "input_params": task.input_params,
                "outputs": task.outputs,
                "input_files": task.input_files,
                "flow_comfy": task.flow_comfy,
                "user_id": task.user_id,
            }
            for task in tasks
        }
    except Exception:
        LOGGER.exception("Failed to retrieve tasks: `%s`, finished=%s", name, finished)
        raise
    finally:
        session.close()


def remove_task_by_id(task_id: int) -> bool:
    if options.VIX_MODE == "WORKER" and options.VIX_HOST:
        return remove_task_by_id_server(task_id)
    return remove_task_by_id_database(task_id)


def remove_task_by_id_database(task_id: int) -> bool:
    session = database.SESSION()
    try:
        lock_result = session.execute(delete(database.TaskLock).where(database.TaskLock.task_id == task_id))
        details_result = session.execute(delete(database.TaskDetails).where(database.TaskDetails.task_id == task_id))
        if lock_result.rowcount + details_result.rowcount > 0:
            session.commit()
            return True
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to remove task: %s", task_id)
        raise
    finally:
        session.close()
        remove_task_files(task_id, ["output", "input"])
    return False


def remove_task_by_id_server(task_id: int) -> bool:
    try:
        r = httpx.delete(options.VIX_HOST.rstrip("/") + "/task", params={"task_id": task_id}, auth=__worker_auth())
        if not httpx.codes.is_error(r.status_code):
            return True
        LOGGER.error("Server return status: %s", r.status_code)
    except Exception as e:
        LOGGER.exception("Exception occurred: %s", e)
    return False


def remove_task_by_name(name: str, user_id: str) -> None:
    tasks_to_delete = get_tasks(name=name, finished=True, user_id=user_id)
    session = database.SESSION()
    try:
        for task_id in tasks_to_delete:
            session.execute(delete(database.TaskLock).where(database.TaskLock.task_id == task_id))
            session.execute(delete(database.TaskDetails).where(database.TaskDetails.task_id == task_id))
            session.commit()
            remove_task_files(task_id, ["output", "input"])
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to remove task by name: %s", name)
        raise
    finally:
        session.close()


def remove_unfinished_task_by_id(task_id: int) -> bool:
    session = database.SESSION()
    try:
        session.execute(delete(database.TaskLock).where(database.TaskLock.task_id == task_id))
        details_result = session.execute(
            delete(database.TaskDetails).where(
                and_(database.TaskDetails.progress != 100.0, database.TaskDetails.task_id == task_id)
            )
        )
        if details_result.rowcount > 0:
            session.commit()
            remove_task_files(task_id, ["output", "input"])
            return True
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to remove task: %s", task_id)
        raise
    finally:
        session.close()
    return False


def remove_unfinished_tasks_by_name(name: str, user_id: str) -> bool:
    session = database.SESSION()
    try:
        stmt = delete(database.TaskDetails).where(
            and_(
                database.TaskDetails.progress != 100.0,
                database.TaskDetails.name == name,
                database.TaskDetails.user_id == user_id,
            )
        )
        result = session.execute(stmt)
        if result.rowcount > 0:
            session.commit()
            return True
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to remove incomplete TaskDetails for `%s`", name)
        raise
    finally:
        session.close()
    return False


def remove_task_files(task_id: int, directories: list[str]) -> None:
    for directory in directories:
        result_prefix = f"{task_id}_"
        target_directory = os.path.join(options.TASKS_FILES_DIR, directory)
        for filename in os.listdir(target_directory):
            if filename.startswith(result_prefix):
                with contextlib.suppress(FileNotFoundError):
                    os.remove(os.path.join(target_directory, filename))


def remove_task_lock(task_id: int) -> None:
    if options.VIX_MODE == "WORKER" and options.VIX_HOST:
        return remove_task_lock_server(task_id)
    return remove_task_lock_database(task_id)


def remove_task_lock_database(task_id: int) -> None:
    session = database.SESSION()
    try:
        result = session.execute(delete(database.TaskLock).where(database.TaskLock.task_id == task_id))
        if result.rowcount > 0:
            session.commit()
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to remove task lock for task_id %s: %s", task_id, e)
    finally:
        session.close()


def remove_task_lock_server(task_id: int) -> None:
    try:
        r = httpx.delete(
            options.VIX_HOST.rstrip("/") + "/task-worker/lock",
            params={"task_id": task_id},
            auth=__worker_auth(),
        )
        if httpx.codes.is_error(r.status_code):
            LOGGER.error("Server return status: %s", r.status_code)
    except Exception as e:
        LOGGER.exception("Exception occurred: %s", e)


def update_task_progress(task_details: dict) -> bool:
    if options.VIX_MODE == "WORKER" and options.VIX_HOST:
        return update_task_progress_server(task_details)
    return update_task_progress_database(task_details["task_id"], task_details["progress"], task_details["error"])


def update_task_progress_database(task_id: int, progress: float, error: str) -> bool:
    session = database.SESSION()
    try:
        result = session.execute(
            update(database.TaskDetails)
            .where(database.TaskDetails.task_id == task_id)
            .values(progress=progress, error=error)
        )
        session.commit()
        return result.rowcount == 1
    except Exception as e:
        interrupt_processing()
        session.rollback()
        LOGGER.exception("Task %s failed to update TaskDetails: %s", task_id, e)
    finally:
        session.close()
    return False


def update_task_progress_server(task_details: dict) -> bool:
    try:
        r = httpx.put(
            options.VIX_HOST.rstrip("/") + "/task-worker/progress",
            data={
                "task_id": task_details["task_id"],
                "progress": task_details["progress"],
                "error": task_details["error"],
            },
            auth=__worker_auth(),
        )
        if not httpx.codes.is_error(r.status_code):
            return True
        LOGGER.error("Server return status: %s", r.status_code)
    except Exception as e:
        LOGGER.exception("Exception occurred: %s", e)
    return False


def remove_active_task_lock():
    if ACTIVE_TASK:
        remove_task_lock(ACTIVE_TASK["task_id"])


def init_active_task_inputs_from_server() -> bool:
    if not (options.VIX_MODE == "WORKER" and options.VIX_HOST):
        return True
    input_directory = os.path.join(options.TASKS_FILES_DIR, "input")
    try:
        for i in enumerate(ACTIVE_TASK["input_files"]):
            r = httpx.get(
                options.VIX_HOST.rstrip("/") + "/task-inputs",
                params={"task_id": ACTIVE_TASK["task_id"], "input_index": i},
                auth=__worker_auth(),
            )
            if httpx.codes.is_error(r.status_code):
                raise f"Can not get input file, status={r.status_code}"
            with builtins.open(os.path.join(input_directory, ACTIVE_TASK["input_files"][i]), mode="wb") as input_file:
                input_file.write(r.content)
        return True
    except Exception as e:
        LOGGER.exception("Can not work on task")
        ACTIVE_TASK["error"] = str(e)
        update_task_progress(ACTIVE_TASK)
        remove_task_files(ACTIVE_TASK["task_id"], ["output", "input"])
        remove_active_task_lock()
        return False


def upload_results_to_server() -> None:
    if not (options.VIX_MODE == "WORKER" and options.VIX_HOST):
        return
    files = []
    result_prefix = str(ACTIVE_TASK["task_id"]) + "_"
    target_directory = os.path.join(options.TASKS_FILES_DIR, "output")
    try:
        for filename in os.listdir(target_directory):
            if filename.startswith(result_prefix):
                fila_path = os.path.join(target_directory, filename)
                file_handle = builtins.open(fila_path, mode="rb")  # pylint: disable=consider-using-with
                files.append(
                    ("files", (filename, file_handle)),
                )
        try:
            r = httpx.put(
                options.VIX_HOST.rstrip("/") + "/task-worker/results",
                params={
                    "task_id": ACTIVE_TASK["task_id"],
                },
                files=files,
                auth=__worker_auth(),
            )
            if httpx.codes.is_error(r.status_code):
                LOGGER.error("Server return status: %s", r.status_code)
        except Exception as e:
            LOGGER.exception("Exception occurred: %s", e)
    finally:
        for f in files:
            f[1][1].close()
    remove_task_files(ACTIVE_TASK["task_id"], ["output", "input"])


def increase_current_task_progress(percent_finished: float) -> None:
    ACTIVE_TASK["progress"] = min(ACTIVE_TASK["progress"] + percent_finished, 99.0)


def task_progress_callback(event: str, data: dict, broadcast: bool = False):
    LOGGER.debug("%s(broadcast=%s): %s", event, broadcast, data)
    if not ACTIVE_TASK:
        LOGGER.warning("ACTIVE_TASK is empty, event = %s.", event)
        return
    node_percent = 99 / ACTIVE_TASK["nodes_count"]

    if event == "executing":
        if not ACTIVE_TASK["current_node"]:
            ACTIVE_TASK["current_node"] = data["node"]
        if ACTIVE_TASK["current_node"] != data["node"]:
            increase_current_task_progress(node_percent)
            ACTIVE_TASK["current_node"] = data["node"]
    elif event == "progress" and "max" in data and "value" in data:
        ACTIVE_TASK["current_node"] = ""
        increase_current_task_progress(node_percent / int(data["max"]))
    elif event == "execution_error":
        ACTIVE_TASK["error"] = data["exception_message"]
        LOGGER.error(
            "Exception occurred during executing task:\n%s\n%s",
            data["exception_message"],
            data["traceback"],
        )
    elif event == "execution_cached":
        increase_current_task_progress((len(data["nodes"]) - 1) * node_percent)
    elif event == "execution_interrupted":
        remove_task_by_id(ACTIVE_TASK["task_id"])
        ACTIVE_TASK["interrupted"] = True
        return
    if not update_task_progress(ACTIVE_TASK):
        interrupt_processing()
        ACTIVE_TASK["interrupted"] = True


def background_prompt_executor(prompt_executor, exit_event: asyncio.Event):
    global ACTIVE_TASK
    last_gc_collect = 0
    need_gc = False
    gc_collect_interval = 10.0

    while True:
        if exit_event.is_set():
            break
        if need_gc:
            current_time = time.perf_counter()
            if (current_time - last_gc_collect) > gc_collect_interval:
                LOGGER.debug("cleanup_models")
                cleanup_models()
                LOGGER.debug("gc.collect")
                gc.collect()
                soft_empty_cache()
                last_gc_collect = current_time
                need_gc = False

        ACTIVE_TASK = get_incomplete_task_without_error(get_installed_flows_names())
        if not ACTIVE_TASK:
            time.sleep(options.PAUSE_INTERVAL)
            continue
        if init_active_task_inputs_from_server() is False:
            ACTIVE_TASK = {}
            continue
        ACTIVE_TASK["nodes_count"] = len(list(ACTIVE_TASK["flow_comfy"].keys()))
        ACTIVE_TASK["current_node"] = ""
        prompt_executor.server.last_prompt_id = str(ACTIVE_TASK["task_id"])
        execution_start_time = time.perf_counter()
        prompt_executor.execute(
            ACTIVE_TASK["flow_comfy"],
            str(ACTIVE_TASK["task_id"]),
            {"client_id": "vix"},
            [str(i["comfy_node_id"]) for i in ACTIVE_TASK["outputs"]],
        )
        current_time = time.perf_counter()
        if ACTIVE_TASK.get("interrupted", False):
            remove_task_by_id(ACTIVE_TASK["task_id"])
        else:
            if not ACTIVE_TASK["error"]:
                ACTIVE_TASK["progress"] = 100.0
                upload_results_to_server()
            update_task_progress(ACTIVE_TASK)
        remove_active_task_lock()
        ACTIVE_TASK = {}
        LOGGER.info("Prompt executed in %f seconds", current_time - execution_start_time)
        need_gc = True


async def start_tasks_engine(comfy_queue: typing.Any, exit_event: asyncio.Event) -> None:
    async def start_background_tasks_engine(prompt_executor):
        await asyncio.to_thread(background_prompt_executor, prompt_executor, exit_event)

    database.init_database_engine()
    if options.VIX_MODE in ("DEFAULT", "WORKER"):
        _ = asyncio.create_task(start_background_tasks_engine(comfy_queue))  # noqa


def __worker_auth() -> tuple[str, str]:
    name, password = options.WORKER_AUTH.split(":")
    return name, password
