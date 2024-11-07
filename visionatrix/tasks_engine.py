import builtins
import contextlib
import gc
import json
import logging
import os
import threading
import time
import typing
from datetime import datetime, timezone

import httpx
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.exc import IntegrityError

from . import database, options
from .comfyui import (
    cleanup_models,
    get_worker_details,
    interrupt_processing,
    soft_empty_cache,
)
from .db_queries import get_global_setting, get_setting
from .flows import get_google_nodes, get_installed_flows, get_ollama_nodes
from .pydantic_models import (
    TaskDetails,
    TaskDetailsShort,
    UserInfo,
    WorkerDetailsRequest,
)
from .tasks_engine_etc import (
    TASK_DETAILS_COLUMNS,
    TASK_DETAILS_COLUMNS_SHORT,
    get_get_incomplete_task_without_error_query,
    init_new_task_details,
    prepare_worker_info_update,
    task_details_from_dict,
    task_details_short_to_dict,
    task_details_to_dict,
)

LOGGER = logging.getLogger("visionatrix")

ACTIVE_TASK: dict = {}


def create_new_task(name: str, input_params: dict, user_info: UserInfo) -> dict:
    with database.SESSION() as session:
        try:
            new_task_queue = database.TaskQueue()
            session.add(new_task_queue)
            session.commit()
        except Exception:
            session.rollback()
            LOGGER.exception("Failed to add `%s` to TaskQueue(%s)", name, user_info.user_id)
            raise
    remove_task_files(new_task_queue.id, ["output", "input"])
    return init_new_task_details(new_task_queue.id, name, input_params, user_info)


def put_task_in_queue(task_details: dict) -> None:
    LOGGER.debug("Put flow in queue: %s", task_details)
    with database.SESSION() as session:
        try:
            session.add(task_details_from_dict(task_details))
            session.commit()
        except Exception:
            session.rollback()
            LOGGER.exception("Failed to put task in queue: %s", task_details["task_id"])
            remove_task_files(task_details["task_id"], ["input"])
            raise


def __get_task_query(task_id: int, user_id: str | None):
    query = (
        select(*TASK_DETAILS_COLUMNS)
        .outerjoin(database.TaskLock, database.TaskLock.task_id == database.TaskDetails.task_id)
        .filter(database.TaskDetails.task_id == task_id)
    )
    if user_id is not None:
        query = query.filter(database.TaskDetails.user_id == user_id)
    return query


def collect_child_task_ids(task: dict | TaskDetailsShort, output_ids: list) -> None:
    if isinstance(task, dict):
        for child in task["child_tasks"]:
            output_ids.append(child["task_id"])
            collect_child_task_ids(child, output_ids)
    else:
        for child in task.child_tasks:
            output_ids.append(child.task_id)
            collect_child_task_ids(child, output_ids)


def fetch_child_tasks(session, parent_task_ids: list[int]) -> dict[int, list[TaskDetailsShort]]:
    if not parent_task_ids:
        return {}

    query = (
        select(*TASK_DETAILS_COLUMNS_SHORT)
        .outerjoin(database.TaskLock, database.TaskLock.task_id == database.TaskDetails.task_id)
        .filter(database.TaskDetails.parent_task_id.in_(parent_task_ids))
    )
    child_tasks = session.execute(query).all()

    parent_to_children = {}
    for task in child_tasks:
        task_details = task_details_short_to_dict(task)
        parent_to_children.setdefault(task.parent_task_id, []).append(task_details)

    next_level_parent_ids = [task.task_id for task in child_tasks]
    next_level_children = fetch_child_tasks(session, next_level_parent_ids)
    for children in parent_to_children.values():
        for child in children:
            child["child_tasks"] = next_level_children.get(child["task_id"], [])
    return parent_to_children


def get_task(task_id: int, user_id: str | None = None, fetch_child: bool = False) -> dict | None:
    with database.SESSION() as session:
        try:
            query = __get_task_query(task_id, user_id)
            task = session.execute(query).one_or_none()
            if task:
                task_dict = task_details_to_dict(task)
                if fetch_child:
                    child_tasks = fetch_child_tasks(session, [task.task_id])
                    task_dict["child_tasks"] = child_tasks.get(task.task_id, [])
                return task_dict
            return None
        except Exception:
            LOGGER.exception("Failed to retrieve task: %s", task_id)
            raise


def get_incomplete_task_without_error(tasks_to_ask: list[str], last_task_name: str) -> dict:
    if options.VIX_MODE == "WORKER" and options.VIX_SERVER:
        task_to_exec = get_incomplete_task_without_error_server(tasks_to_ask, last_task_name)
    else:
        task_to_exec = get_incomplete_task_without_error_database(
            database.DEFAULT_USER.user_id,
            WorkerDetailsRequest.model_validate(get_worker_details()),
            tasks_to_ask,
            last_task_name,
        )
    if not task_to_exec:
        return {}

    ollama_nodes = get_ollama_nodes(task_to_exec["flow_comfy"])
    if ollama_nodes:
        ollama_vision_model = ""
        if [i for i in ollama_nodes if task_to_exec["flow_comfy"][i]["class_type"] == "OllamaVision"]:
            ollama_vision_model = get_worker_value("OLLAMA_VISION_MODEL", task_to_exec["user_id"])
        ollama_url = get_worker_value("OLLAMA_URL", task_to_exec["user_id"])

        for node in ollama_nodes:
            if ollama_url:
                task_to_exec["flow_comfy"][node]["inputs"]["url"] = ollama_url
            if ollama_vision_model and task_to_exec["flow_comfy"][node]["class_type"] == "OllamaVision":
                task_to_exec["flow_comfy"][node]["inputs"]["model"] = ollama_vision_model

    google_nodes = get_google_nodes(task_to_exec["flow_comfy"])
    if google_nodes:
        google_proxy = get_worker_value("GOOGLE_PROXY", task_to_exec["user_id"])
        google_api_key = get_worker_value("GOOGLE_API_KEY", task_to_exec["user_id"])
        gemini_model = get_worker_value("GEMINI_MODEL", task_to_exec["user_id"])
        for node in google_nodes:
            if google_api_key:
                task_to_exec["flow_comfy"][node]["inputs"]["api_key"] = google_api_key
                task_to_exec["flow_comfy"][node]["inputs"]["proxy"] = google_proxy
                if gemini_model:
                    task_to_exec["flow_comfy"][node]["inputs"]["model"] = gemini_model

    return task_to_exec


def get_worker_value(key_name: str, user_id: str = "") -> str:
    key_value = os.environ.get(key_name.upper(), "")
    if key_value:
        return key_value
    if options.VIX_MODE == "WORKER" and options.VIX_SERVER:
        r = httpx.get(
            options.VIX_SERVER.rstrip("/") + "/api/settings/get",
            params={"key": key_name.lower()},
            auth=options.worker_auth(),
            timeout=float(options.WORKER_NET_TIMEOUT),
        )
        if httpx.codes.is_error(r.status_code):
            LOGGER.error("Can not fetch `%s` from the server: %s", key_name, r.status_code)
        else:
            key_value = r.text
    elif user_id:
        key_value = get_setting(user_id, key_name.lower(), True)
    else:
        key_value = get_global_setting(key_name.lower(), True)
    return key_value


def get_incomplete_task_without_error_server(tasks_to_ask: list[str], last_task_name: str) -> dict:
    try:
        r = httpx.post(
            options.VIX_SERVER.rstrip("/") + "/api/tasks/next",
            json={
                "worker_details": get_worker_details(),
                "tasks_names": tasks_to_ask,
                "last_task_name": last_task_name,
            },
            auth=options.worker_auth(),
            timeout=float(options.WORKER_NET_TIMEOUT),
        )
        if r.status_code == httpx.codes.NO_CONTENT:
            return {}
        if not httpx.codes.is_error(r.status_code):
            return json.loads(r.text)
        LOGGER.error("Server return status: %s", r.status_code)
    except Exception as e:
        LOGGER.exception("Connect exception occurred")
        if isinstance(e, httpx.ConnectError):
            time.sleep(5)
    return {}


def get_incomplete_task_without_error_database(
    worker_user_id: str,
    worker_details: WorkerDetailsRequest,
    tasks_to_ask: list[str],
    last_task_name: str,
    user_id: str | None = None,
) -> dict:
    if not tasks_to_ask:
        return {}
    session = database.SESSION()
    try:
        worker_id, worker_device_name, worker_info_values = prepare_worker_info_update(worker_user_id, worker_details)
        result = session.execute(
            update(database.Worker).where(database.Worker.worker_id == worker_id).values(**worker_info_values)
        )
        tasks_to_give = []
        if result.rowcount == 0:
            session.add(
                database.Worker(
                    user_id=worker_user_id,
                    worker_id=worker_id,
                    device_name=worker_device_name,
                    **worker_info_values,
                )
            )
        else:
            query = select(database.Worker).filter(database.Worker.worker_id == worker_id)
            tasks_to_give = session.execute(query).scalar().tasks_to_give
        query = get_get_incomplete_task_without_error_query(tasks_to_ask, tasks_to_give, last_task_name, user_id)
        task = session.execute(query).scalar()
        if not task:
            session.commit()
            return {}
        return lock_task_and_return_details(session, task)
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to retrieve task for processing: %s", e)
        return {}
    finally:
        session.close()


def __lock_task_and_return_details(task: type[database.TaskDetails] | database.TaskDetails):
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
        "execution_time": 0.0,
        "webhook_url": task.webhook_url,
        "webhook_headers": task.webhook_headers,
    }


def lock_task_and_return_details(session, task: type[database.TaskDetails] | database.TaskDetails) -> dict:
    try:
        session.add(database.TaskLock(task_id=task.task_id, locked_at=datetime.utcnow()))
        session.commit()
        return __lock_task_and_return_details(task)
    except IntegrityError:
        session.rollback()
        return {}


def __get_tasks_query(
    name: str | None,
    group_scope: int,
    finished: bool | None,
    user_id: str | None,
    full_info=True,
    only_parent=False,
):
    query = select(*(TASK_DETAILS_COLUMNS if full_info else TASK_DETAILS_COLUMNS_SHORT)).outerjoin(
        database.TaskLock, database.TaskLock.task_id == database.TaskDetails.task_id
    )

    if user_id is not None:
        query = query.filter(database.TaskDetails.user_id == user_id)
    if name is not None:
        query = query.filter(database.TaskDetails.name == name)
    if finished is not None:
        if finished:
            query = query.filter(database.TaskDetails.progress == 100.0)
        else:
            query = query.filter(database.TaskDetails.progress < 100.0)
    if only_parent:
        query = query.filter(
            (database.TaskDetails.parent_task_id == None)  # noqa # pylint: disable=singleton-comparison
            | (database.TaskDetails.parent_task_id == 0)
        )
    if group_scope:
        query = query.filter(database.TaskDetails.group_scope == group_scope)
    return query


def get_tasks(
    name: str | None = None,
    group_scope: int = 1,
    finished: bool | None = None,
    user_id: str | None = None,
    fetch_child: bool = False,
    only_parent: bool = False,
) -> dict[int, TaskDetails]:
    with database.SESSION() as session:
        try:
            query = __get_tasks_query(name, group_scope, finished, user_id, only_parent=only_parent)
            results = session.execute(query).all()
            tasks = {}
            task_ids = [task.task_id for task in results]
            child_tasks = fetch_child_tasks(session, task_ids) if fetch_child else {}
            for task in results:
                task_details = task_details_to_dict(task)
                task_details["child_tasks"] = child_tasks.get(task.task_id, [])
                tasks[task.task_id] = TaskDetails.model_validate(task_details)
            return tasks
        except Exception:
            LOGGER.exception("Failed to retrieve tasks: `%s`, finished=%s", name, finished)
            raise


def get_tasks_short(
    user_id: str,
    name: str | None = None,
    group_scope: int = 1,
    finished: bool | None = None,
    fetch_child: bool = False,
    only_parent: bool = False,
) -> dict[int, TaskDetailsShort]:
    with database.SESSION() as session:
        try:
            query = __get_tasks_query(name, group_scope, finished, user_id, full_info=False, only_parent=only_parent)
            results = session.execute(query).all()
            tasks = {}
            task_ids = [task.task_id for task in results]
            child_tasks = fetch_child_tasks(session, task_ids) if fetch_child else {}
            for task in results:
                task_details = task_details_short_to_dict(task)
                task_details["child_tasks"] = child_tasks.get(task.task_id, [])
                tasks[task.task_id] = TaskDetailsShort.model_validate(task_details)
            return tasks
        except Exception:
            LOGGER.exception("Failed to retrieve tasks: `%s`, finished=%s", name, finished)
            raise


def remove_task_by_id(task_id: int) -> bool:
    if options.VIX_MODE == "WORKER" and options.VIX_SERVER:
        return remove_task_by_id_server(task_id)
    return remove_task_by_id_database([task_id])


def remove_task_by_id_database(task_ids: list[int]) -> bool:
    session = database.SESSION()
    try:
        lock_result = session.execute(delete(database.TaskLock).where(database.TaskLock.task_id.in_(task_ids)))
        details_result = session.execute(delete(database.TaskDetails).where(database.TaskDetails.task_id.in_(task_ids)))
        if lock_result.rowcount + details_result.rowcount > 0:
            session.commit()
            return True
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to remove tasks: %s", task_ids)
        raise
    finally:
        session.close()
        for i in task_ids:
            remove_task_files(i, ["output", "input"])
    return False


def remove_task_by_id_server(task_id: int) -> bool:
    try:
        r = httpx.delete(
            options.VIX_SERVER.rstrip("/") + "/api/tasks/task",
            params={"task_id": task_id},
            auth=options.worker_auth(),
            timeout=float(options.WORKER_NET_TIMEOUT),
        )
        if not httpx.codes.is_error(r.status_code):
            return True
        LOGGER.warning("Task %s: server return status: %s", task_id, r.status_code)
    except Exception as e:
        LOGGER.exception("Task %s: exception occurred: %s", task_id, e)
    return False


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


def remove_unfinished_tasks_by_name_and_group(name: str, user_id: str, group_scope: int) -> bool:
    session = database.SESSION()
    try:
        stmt = delete(database.TaskDetails).where(
            and_(
                database.TaskDetails.progress != 100.0,
                database.TaskDetails.name == name,
                database.TaskDetails.user_id == user_id,
                (database.TaskDetails.group_scope == group_scope if group_scope else True),
                or_(
                    database.TaskDetails.parent_task_id == None,  # noqa # pylint: disable=singleton-comparison
                    database.TaskDetails.parent_task_id == 0,
                ),
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


def get_task_files(task_id: int, directory: typing.Literal["input", "output"]) -> list[tuple[str, str]]:
    result_prefix = str(task_id) + "_"
    target_directory = os.path.join(options.TASKS_FILES_DIR, directory)
    r = []
    for filename in sorted(os.listdir(target_directory)):
        if filename.startswith(result_prefix):
            r.append((filename, os.path.join(target_directory, filename)))
    return r


def remove_task_files(task_id: int, directories: list[str]) -> None:
    for directory in directories:
        result_prefix = f"{task_id}_"
        target_directory = os.path.join(options.TASKS_FILES_DIR, directory)
        for filename in os.listdir(target_directory):
            if filename.startswith(result_prefix):
                with contextlib.suppress(FileNotFoundError):
                    os.remove(os.path.join(target_directory, filename))


def remove_task_lock(task_id: int) -> None:
    if options.VIX_MODE == "WORKER" and options.VIX_SERVER:
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
        LOGGER.exception("Task %s: failed to remove task lock: %s", task_id, e)
    finally:
        session.close()


def remove_task_lock_server(task_id: int) -> None:
    try:
        r = httpx.delete(
            options.VIX_SERVER.rstrip("/") + "/api/tasks/lock",
            params={"task_id": task_id},
            auth=options.worker_auth(),
            timeout=float(options.WORKER_NET_TIMEOUT),
        )
        if httpx.codes.is_error(r.status_code):
            LOGGER.warning("Task %s: server return status: %s", task_id, r.status_code)
    except Exception as e:
        LOGGER.exception("Exception occurred: %s", e)


def update_task_outputs(task_id: int, outputs: list[dict]) -> bool:
    with database.SESSION() as session:
        try:
            result = session.execute(
                update(database.TaskDetails).where(database.TaskDetails.task_id == task_id).values(outputs=outputs)
            )
            if result.rowcount == 1:
                session.commit()
                return True
        except Exception as e:
            interrupt_processing()
            session.rollback()
            LOGGER.exception("Task %s: failed to update TaskDetails outputs: %s", task_id, e)
    return False


def update_task_progress(task_details: dict) -> bool:
    __update_temporary_execution_time(task_details)
    if options.VIX_MODE == "WORKER" and options.VIX_SERVER:
        return update_task_progress_server(task_details)
    r = update_task_progress_database(
        task_details["task_id"],
        task_details["progress"],
        task_details["error"],
        task_details["execution_time"],
        database.DEFAULT_USER.user_id,
        WorkerDetailsRequest.model_validate(get_worker_details()),
    )
    if r and task_details["webhook_url"]:
        try:
            with httpx.Client(base_url=task_details["webhook_url"], timeout=3.0) as client:
                client.post(
                    url="task-progress",
                    json={
                        "task_id": task_details["task_id"],
                        "progress": task_details["progress"],
                        "execution_time": task_details["execution_time"],
                        "error": task_details["error"],
                    },
                    headers=task_details["webhook_headers"],
                )
        except httpx.RequestError as e:
            LOGGER.exception(
                "Exception during calling webhook %s, progress=%s: %s",
                task_details["webhook_url"],
                task_details["progress"],
                e,
            )
    return r


def update_task_progress_database(
    task_id: int,
    progress: float,
    error: str,
    execution_time: float,
    worker_user_id: str,
    worker_details: WorkerDetailsRequest,
) -> bool:
    with database.SESSION() as session:
        try:
            worker_id, _, worker_info_values = prepare_worker_info_update(worker_user_id, worker_details)
            update_values = {
                "progress": progress,
                "error": error,
                "execution_time": execution_time,
                "updated_at": datetime.now(timezone.utc),
                "worker_id": worker_id,
            }
            if progress == 100.0:
                update_values["finished_at"] = datetime.now(timezone.utc)
            result = session.execute(
                update(database.TaskDetails).where(database.TaskDetails.task_id == task_id).values(**update_values)
            )
            session.commit()
            if (task_updated := result.rowcount == 1) is True:
                session.execute(
                    update(database.Worker).where(database.Worker.worker_id == worker_id).values(**worker_info_values)
                )
                session.commit()
            return task_updated
        except Exception as e:
            interrupt_processing()
            session.rollback()
            LOGGER.exception("Task %s: failed to update TaskDetails: %s", task_id, e)
    return False


def task_restart_database(task_id: int) -> bool:
    with database.SESSION() as session:
        try:
            update_values = {
                "progress": 0.0,
                "error": "",
                "execution_time": 0.0,
                "updated_at": datetime.now(timezone.utc),
                "worker_id": None,
            }
            result = session.execute(
                update(database.TaskDetails).where(database.TaskDetails.task_id == task_id).values(**update_values)
            )
            session.commit()
            return result.rowcount == 1
        except Exception as e:
            interrupt_processing()
            session.rollback()
            LOGGER.exception("Task %s: failed to restart: %s", task_id, e)
    return False


def update_task_progress_server(task_details: dict) -> bool:
    task_id = task_details["task_id"]
    request_data = {
        "worker_details": get_worker_details(),
        "task_id": task_id,
        "progress": task_details["progress"],
        "execution_time": task_details["execution_time"],
        "error": task_details["error"],
    }
    for i in range(3):
        try:
            r = httpx.put(
                options.VIX_SERVER.rstrip("/") + "/api/tasks/progress",
                json=request_data,
                auth=options.worker_auth(),
                timeout=float(options.WORKER_NET_TIMEOUT),
            )
            if not httpx.codes.is_error(r.status_code):
                return True
            if r.status_code == 404:
                LOGGER.info("Task %s: missing on server.", task_id)
            else:
                LOGGER.error("Task %s: server return status: %s", task_id, r.status_code)
            return False
        except (httpx.TimeoutException, httpx.RemoteProtocolError):
            if i != 2:
                LOGGER.warning("Task %s: attempt number %s: timeout or protocol exception occurred", task_id, i)
                continue
            LOGGER.error("Task %s: attempt number %s: timeout or protocol exception occurred, task failed.", task_id, i)
    return False


def __update_temporary_execution_time(task_details: dict) -> None:
    if task_details["progress"] == 100.0 or task_details["error"] or task_details.get("interrupted", False):
        return
    if "execution_start_time" in task_details:
        task_details["execution_time"] = time.perf_counter() - task_details["execution_start_time"]


def remove_active_task_lock():
    if ACTIVE_TASK:
        remove_task_lock(ACTIVE_TASK["task_id"])


def init_active_task_inputs_from_server() -> bool:
    if not (options.VIX_MODE == "WORKER" and options.VIX_SERVER):
        return True
    task_id = ACTIVE_TASK["task_id"]
    remove_task_files(task_id, ["output", "input"])
    input_directory = os.path.join(options.TASKS_FILES_DIR, "input")
    try:
        for i, _ in enumerate(ACTIVE_TASK["input_files"]):
            for k in range(3):
                try:
                    r = httpx.get(
                        options.VIX_SERVER.rstrip("/") + "/api/tasks/inputs",
                        params={"task_id": task_id, "input_index": i},
                        auth=options.worker_auth(),
                        timeout=float(options.WORKER_NET_TIMEOUT),
                    )
                    if r.status_code == httpx.codes.NOT_FOUND:
                        raise RuntimeError(f"Task {task_id}: not found on server")
                    if httpx.codes.is_error(r.status_code):
                        raise RuntimeError(f"Task {task_id}: can not get input file, status={r.status_code}")
                    with builtins.open(
                        os.path.join(input_directory, ACTIVE_TASK["input_files"][i]["file_name"]), mode="wb"
                    ) as input_file:
                        input_file.write(r.content)
                    break
                except (httpx.TimeoutException, httpx.RemoteProtocolError):
                    if k != 2:
                        LOGGER.warning("Task %s: attempt number %s: timeout or protocol exception occurred", task_id, i)
                        continue
                    raise
        return True
    except Exception as e:
        LOGGER.exception("Can not work on task")
        ACTIVE_TASK["error"] = str(e)
        update_task_progress(ACTIVE_TASK)
        remove_task_files(task_id, ["output", "input"])
        remove_task_lock(task_id)
        return False


def upload_results_to_server(task_details: dict) -> bool:
    task_id = task_details["task_id"]
    output_files = get_task_files(task_id, "output")
    if not (options.VIX_MODE == "WORKER" and options.VIX_SERVER):
        for task_output in task_details["outputs"]:
            task_file_prefix = f"{task_id}_{task_output['comfy_node_id']}_"
            relevant_files = [file_info for file_info in output_files if file_info[0].startswith(task_file_prefix)]
            file_size = 0
            batch_size = 0
            for i in relevant_files:
                file_size += os.path.getsize(i[1])
                batch_size += 1
            task_output["file_size"] = file_size
            task_output["batch_size"] = batch_size
        update_task_outputs(task_id, task_details["outputs"])
        return True
    files = []
    try:
        for output_file in output_files:
            file_handle = builtins.open(output_file[1], mode="rb")  # noqa pylint: disable=consider-using-with
            files.append(
                ("files", (output_file[0], file_handle)),
            )
        try:
            for i in range(3):
                try:
                    r = httpx.put(
                        options.VIX_SERVER.rstrip("/") + "/api/tasks/results",
                        params={
                            "task_id": task_id,
                        },
                        files=files,
                        auth=options.worker_auth(),
                        timeout=float(options.WORKER_NET_TIMEOUT),
                    )
                    if r.status_code == httpx.codes.NOT_FOUND:
                        return False
                    if not httpx.codes.is_error(r.status_code):
                        return True
                    LOGGER.error("Task %s: server return status: %s", task_id, r.status_code)
                except (httpx.TimeoutException, httpx.RemoteProtocolError):
                    if i != 2:
                        LOGGER.warning("Task %s: attempt number %s: timeout or protocol exception occurred", task_id, i)
                        continue
                    LOGGER.error(
                        "Task %s: attempt number %s: timeout or protocol exception occurred, task failed.", task_id, i
                    )
        except Exception as e:
            LOGGER.exception("Task %s: exception occurred: %s", task_id, e)
    finally:
        for f in files:
            f[1][1].close()
        remove_task_files(task_id, ["output", "input"])
    return False


def increase_current_task_progress(percent_finished: float) -> None:
    ACTIVE_TASK["progress"] = min(ACTIVE_TASK["progress"] + percent_finished, 99.0)


def task_progress_callback(event: str, data: dict, broadcast: bool = False):
    LOGGER.debug("%s(broadcast=%s): %s", event, broadcast, data)
    if not ACTIVE_TASK:
        LOGGER.warning("ACTIVE_TASK is empty, event = %s.", event)
        return
    node_percent = 99 / ACTIVE_TASK["nodes_count"]

    if event == "executing":
        if options.NODES_TIMING:
            last_node_id_timing = ACTIVE_TASK.get("timing_last_node_id", 0)
            current_time = time.perf_counter()
            if last_node_id_timing and last_node_id_timing != data["node"]:
                LOGGER.log(
                    LOGGER.getEffectiveLevel(),
                    "Flow %s, node %s execution time: %s",
                    ACTIVE_TASK["task_id"],
                    data["node"],
                    current_time - ACTIVE_TASK["timing_last_time"],
                )
            ACTIVE_TASK["timing_last_node_id"] = data["node"]
            ACTIVE_TASK["timing_last_time"] = current_time
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
    elif event == "execution_cached" and len(data["nodes"]) > 1:
        increase_current_task_progress((len(data["nodes"]) - 1) * node_percent)
    elif event == "execution_interrupted":
        ACTIVE_TASK["interrupted"] = True


def background_prompt_executor(prompt_executor, exit_event: threading.Event):
    global ACTIVE_TASK
    reply_count_no_tasks = 0
    last_task_name = ""
    last_gc_collect = 0
    need_gc = False

    import torch  # noqa

    while True:
        if need_gc:
            current_time = time.perf_counter()
            if (current_time - last_gc_collect) > options.GC_COLLECT_INTERVAL:
                LOGGER.debug("cleanup_models")
                cleanup_models()
                LOGGER.debug("gc.collect")
                gc.collect()
                LOGGER.debug("soft_empty_cache")
                soft_empty_cache(True)
                last_gc_collect = current_time
                need_gc = False

        if exit_event.wait(
            min(
                options.MIN_PAUSE_INTERVAL + reply_count_no_tasks * options.MAX_PAUSE_INTERVAL / 10,
                options.MAX_PAUSE_INTERVAL,
            ),
        ):
            break

        ACTIVE_TASK = get_incomplete_task_without_error(list(get_installed_flows()), last_task_name)
        if not ACTIVE_TASK:
            reply_count_no_tasks = min(reply_count_no_tasks + 1, 10)
            continue
        if init_active_task_inputs_from_server() is False:
            ACTIVE_TASK = {}
            continue
        last_task_name = ACTIVE_TASK["name"]
        ACTIVE_TASK["nodes_count"] = len(list(ACTIVE_TASK["flow_comfy"].keys()))
        ACTIVE_TASK["current_node"] = ""
        prompt_executor.server.last_prompt_id = str(ACTIVE_TASK["task_id"])
        if options.GPU_MEM_TRACKING and torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        execution_start_time = time.perf_counter()
        ACTIVE_TASK["execution_start_time"] = execution_start_time
        threading.Thread(target=update_task_progress_thread, args=(ACTIVE_TASK,), daemon=True).start()
        prompt_executor.execute(
            ACTIVE_TASK["flow_comfy"],
            str(ACTIVE_TASK["task_id"]),
            {"client_id": "vix"},
            [str(i["comfy_node_id"]) for i in ACTIVE_TASK["outputs"]],
        )
        current_time = time.perf_counter()
        if ACTIVE_TASK.get("interrupted", False) is False and not ACTIVE_TASK["error"]:
            ACTIVE_TASK["execution_time"] = current_time - execution_start_time
            if options.GPU_MEM_TRACKING and torch.cuda.is_available():
                max_mem = torch.cuda.max_memory_allocated() / 1024**2
                LOGGER.log(
                    LOGGER.getEffectiveLevel(),
                    "Flow %s with id=%s consumed a maximum of %.2f MB",
                    ACTIVE_TASK["name"],
                    ACTIVE_TASK["task_id"],
                    max_mem,
                )
            ACTIVE_TASK["progress"] = 100.0
        ACTIVE_TASK = {}
        LOGGER.info("Prompt executed in %f seconds", current_time - execution_start_time)
        need_gc = True


def update_task_progress_thread(active_task: dict) -> None:
    last_info = active_task.copy()
    try:
        while True:
            if last_info != active_task:
                last_info = active_task.copy()
                if last_info["progress"] == 100.0:
                    if upload_results_to_server(last_info):
                        update_task_progress(last_info)
                    break
                if not update_task_progress(last_info):
                    active_task["interrupted"] = True
                    interrupt_processing()
                    break
                if last_info["error"]:
                    break
                active_task["execution_time"] = last_info["execution_time"]
            else:
                time.sleep(0.1)
    finally:
        remove_task_lock(last_info["task_id"])


def update_task_info_database(task_id: int, update_fields: dict) -> bool:
    with database.SESSION() as session:
        try:
            result = session.execute(
                update(database.TaskDetails)
                .where(database.TaskDetails.task_id == task_id, database.TaskDetails.progress == 0.0)
                .values(**update_fields)
            )
            session.commit()
            return result.rowcount == 1
        except Exception as e:
            session.rollback()
            LOGGER.exception("Task %s: failed to update task info: %s", task_id, e)
            return False
