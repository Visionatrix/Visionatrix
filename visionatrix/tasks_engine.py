import asyncio
import builtins
import contextlib
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

from . import comfyui_wrapper, database, models_map, options
from .db_queries import (
    get_global_setting,
    get_installed_models,
    get_setting,
    worker_increment_empty_task_requests_count,
    worker_reset_empty_task_requests_count,
)
from .flows import (
    get_google_nodes,
    get_insightface_nodes,
    get_installed_flows,
    get_ollama_nodes,
    get_remote_vae_switches,
)
from .pydantic_models import (
    ExecutionDetails,
    TaskDetailsShort,
    WorkerDetailsRequest,
)
from .tasks_engine_etc import (
    TASK_DETAILS_COLUMNS,
    TASK_DETAILS_COLUMNS_SHORT,
    get_incomplete_task_without_error_query,
    nodes_execution_profiler,
    prepare_worker_info_update,
)
from .webhooks import webhook_task_progress

LOGGER = logging.getLogger("visionatrix")

ACTIVE_TASK: dict = {}


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


async def get_incomplete_task_without_error(last_task_name: str) -> dict:
    tasks_to_ask = list(await get_installed_flows())
    if options.VIX_MODE == "WORKER" and options.VIX_SERVER:
        if not (task_to_exec := await get_incomplete_task_without_error_server(tasks_to_ask, last_task_name)):
            return {}
    else:
        task_to_exec = await get_incomplete_task_without_error_database(
            database.DEFAULT_USER.user_id,
            WorkerDetailsRequest.model_validate(comfyui_wrapper.get_worker_details()),
            tasks_to_ask,
            last_task_name,
        )
        if not task_to_exec:
            return {}

    await task_preprocess_extra_flags(task_to_exec["extra_flags"])
    ollama_nodes = get_ollama_nodes(task_to_exec["flow_comfy"])
    if ollama_nodes:
        ollama_vision_model = ""
        if [i for i in ollama_nodes if task_to_exec["flow_comfy"][i]["class_type"] == "OllamaVision"]:
            ollama_vision_model = await get_worker_value("OLLAMA_VISION_MODEL", task_to_exec["user_id"])
        ollama_llm_model = ""
        if [
            i
            for i in ollama_nodes
            if task_to_exec["flow_comfy"][i]["class_type"]
            in (
                "OllamaGenerate",
                "OllamaGenerateAdvance",
                "OllamaConnectivityV2",
            )
        ]:
            ollama_llm_model = await get_worker_value("OLLAMA_LLM_MODEL", task_to_exec["user_id"])
        ollama_url = await get_worker_value("OLLAMA_URL", task_to_exec["user_id"])
        ollama_keepalive = await get_worker_value("OLLAMA_KEEPALIVE", task_to_exec["user_id"])

        for node in ollama_nodes:
            if ollama_url:
                task_to_exec["flow_comfy"][node]["inputs"]["url"] = ollama_url
            if ollama_keepalive:
                task_to_exec["flow_comfy"][node]["inputs"]["keep_alive"] = ollama_keepalive
            if ollama_vision_model and task_to_exec["flow_comfy"][node]["class_type"] == "OllamaVision":
                task_to_exec["flow_comfy"][node]["inputs"]["model"] = ollama_vision_model
            if ollama_llm_model and task_to_exec["flow_comfy"][node]["class_type"] in (
                "OllamaGenerate",
                "OllamaGenerateAdvance",
                "OllamaConnectivityV2",
            ):
                task_to_exec["flow_comfy"][node]["inputs"]["model"] = ollama_llm_model

    google_nodes = get_google_nodes(task_to_exec["flow_comfy"])
    if google_nodes:
        google_proxy = await get_worker_value("GOOGLE_PROXY", task_to_exec["user_id"])
        google_api_key = await get_worker_value("GOOGLE_API_KEY", task_to_exec["user_id"])
        gemini_model = await get_worker_value("GEMINI_MODEL", task_to_exec["user_id"])
        for node in google_nodes:
            if google_api_key:
                task_to_exec["flow_comfy"][node]["inputs"]["api_key"] = google_api_key
                task_to_exec["flow_comfy"][node]["inputs"]["proxy"] = google_proxy
                if gemini_model:
                    task_to_exec["flow_comfy"][node]["inputs"]["model"] = gemini_model

    remote_vae_switches = get_remote_vae_switches(task_to_exec["flow_comfy"])
    if remote_vae_switches:
        remote_vae_flows = await get_worker_value("remote_vae_flows", task_to_exec["user_id"])
        if remote_vae_flows:
            remote_vae_flows_list = json.loads(remote_vae_flows)
            if task_to_exec["name"] in remote_vae_flows_list:
                for node in remote_vae_switches:
                    task_to_exec["flow_comfy"][node]["inputs"]["state"] = True

    await task_preprocess_insightface_nodes(task_to_exec["flow_comfy"], task_to_exec["user_id"])

    models_map.process_flow_models(task_to_exec["flow_comfy"], await get_installed_models())

    return task_to_exec


async def task_preprocess_extra_flags(extra_flags: dict) -> None:
    comfyui_wrapper.set_comfy_internal_flags(
        extra_flags.get("save_metadata", False),
        extra_flags.get("smart_memory", True),
        extra_flags.get("cache_type", "classic"),
        extra_flags.get("cache_size", 1),
        extra_flags.get("vae_cpu", False),
    )


async def task_preprocess_insightface_nodes(flow_comfy: dict, user_id: str) -> None:
    insightface_nodes = get_insightface_nodes(flow_comfy)
    if not insightface_nodes:
        return
    insightface_provider = await get_worker_value("insightface_provider", user_id)
    if not insightface_provider:
        return
    for node in insightface_nodes:
        node_details = flow_comfy[node]
        if "insightface" in node_details["inputs"] and node_details["class_type"] == "InfiniteYouApply":
            flow_comfy[node]["inputs"]["insightface"] = insightface_provider
        elif "provider" in node_details["inputs"]:
            flow_comfy[node]["inputs"]["provider"] = insightface_provider
        else:
            LOGGER.warning("Can not set `insightface_provider` for node %s.", node_details["class_type"])


async def get_worker_value(key_name: str, user_id: str = "") -> str:
    key_value = os.environ.get(key_name.upper(), "")
    if key_value:
        return key_value
    if options.VIX_MODE == "WORKER" and options.VIX_SERVER:
        async with httpx.AsyncClient(timeout=options.WORKER_NET_TIMEOUT) as client:
            r = await client.get(
                options.VIX_SERVER.rstrip("/") + "/vapi/settings/get",
                params={"key": key_name.lower()},
                auth=options.worker_auth(),
            )
        if httpx.codes.is_error(r.status_code):
            LOGGER.error("Can not fetch `%s` from the server: %s", key_name, r.status_code)
        else:
            key_value = r.text
    elif user_id:
        key_value = await get_setting(user_id, key_name.lower(), True)
    else:
        key_value = await get_global_setting(key_name.lower(), True)
    return key_value


async def get_incomplete_task_without_error_server(tasks_to_ask: list[str], last_task_name: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=options.WORKER_NET_TIMEOUT) as client:
            r = await client.post(
                options.VIX_SERVER.rstrip("/") + "/vapi/tasks/next",
                json={
                    "worker_details": comfyui_wrapper.get_worker_details(),
                    "tasks_names": tasks_to_ask,
                    "last_task_name": last_task_name,
                },
                auth=options.worker_auth(),
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


async def get_task_for_federated_worker(
    tasks_to_ask: list[str],
) -> dict:
    if not tasks_to_ask:
        return {}
    async with database.SESSION() as session:
        try:
            query = get_incomplete_task_without_error_query(tasks_to_ask, [], "", "non-existing", None)
            task = (await session.execute(query)).scalar()
            if not task:
                return {}
            return await lock_task_and_return_details(session, task)
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to retrieve task for processing: %s", e)
            return {}


async def get_incomplete_task_without_error_database(
    worker_user_id: str,
    worker_details: WorkerDetailsRequest,
    tasks_to_ask: list[str],
    last_task_name: str,
    user_id: str | None = None,
) -> dict:
    async with database.SESSION() as session:
        try:
            worker_id, worker_device_name, worker_info_values = prepare_worker_info_update(
                worker_user_id, worker_details
            )
            worker_info_values["last_asked_tasks"] = tasks_to_ask
            result = await session.execute(
                update(database.Worker).where(database.Worker.worker_id == worker_id).values(**worker_info_values)
            )
            new_worker = result.rowcount == 0
            if new_worker:
                session.add(
                    database.Worker(
                        user_id=worker_user_id,
                        worker_id=worker_id,
                        device_name=worker_device_name,
                        **worker_info_values,
                    )
                )
            await session.commit()
            if not tasks_to_ask:
                return {}

            worker_record = None
            if not new_worker:
                # just an optimization to not fetch the worker settings if it's a newly created worker
                query = select(database.Worker).filter(database.Worker.worker_id == worker_id)
                worker_record = (await session.execute(query)).scalar()

            query = get_incomplete_task_without_error_query(
                tasks_to_ask, worker_record.tasks_to_give if worker_record else [], last_task_name, worker_id, user_id
            )
            task = (await session.execute(query)).scalar()
            if not task:
                await worker_increment_empty_task_requests_count(worker_id)
                return {}
            task_details = await lock_task_and_return_details(session, task)
            if task_details:
                await worker_reset_empty_task_requests_count(worker_id)
                if worker_record:
                    worker_specific_settings_map = {
                        "smart_memory": worker_record.smart_memory,
                        "cache_type": worker_record.cache_type,
                        "cache_size": worker_record.cache_size,
                        "vae_cpu": worker_record.vae_cpu,
                    }
                    for setting_name, worker_value in worker_specific_settings_map.items():
                        if worker_value is not None:
                            task_details["extra_flags"][setting_name] = worker_value
            return task_details
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to retrieve task for processing: %s", e)
            return {}


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
        "extra_flags": task.extra_flags,
        "translated_input_params": task.translated_input_params,
    }


async def lock_task_and_return_details(session, task: type[database.TaskDetails] | database.TaskDetails) -> dict:
    try:
        session.add(database.TaskLock(task_id=task.task_id, locked_at=datetime.utcnow()))
        await session.commit()
        return __lock_task_and_return_details(task)
    except IntegrityError:
        await session.rollback()
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


async def remove_task_by_id_database(task_ids: list[int]) -> bool:
    session = database.SESSION()
    try:
        lock_result = await session.execute(delete(database.TaskLock).where(database.TaskLock.task_id.in_(task_ids)))
        details_result = await session.execute(
            delete(database.TaskDetails).where(database.TaskDetails.task_id.in_(task_ids))
        )
        if lock_result.rowcount + details_result.rowcount > 0:
            await session.commit()
            return True
    except Exception:
        await session.rollback()
        LOGGER.exception("Failed to remove tasks: %s", task_ids)
        raise
    finally:
        await session.close()
        for i in task_ids:
            remove_task_files(i, ["output", "input"])
    return False


async def remove_unfinished_task_by_id(task_id: int) -> bool:
    session = database.SESSION()
    try:
        await session.execute(delete(database.TaskLock).where(database.TaskLock.task_id == task_id))
        details_result = await session.execute(
            delete(database.TaskDetails).where(
                and_(database.TaskDetails.progress != 100.0, database.TaskDetails.task_id == task_id)
            )
        )
        if details_result.rowcount > 0:
            await session.commit()
            remove_task_files(task_id, ["output", "input"])
            return True
    except Exception:
        await session.rollback()
        LOGGER.exception("Failed to remove task: %s", task_id)
        raise
    finally:
        await session.close()
    return False


async def remove_unfinished_tasks_by_name_and_group(name: str, user_id: str, group_scope: int) -> bool:
    async with database.SESSION() as session:
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
            result = await session.execute(stmt)
            if result.rowcount > 0:
                await session.commit()
                return True
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to remove incomplete TaskDetails for `%s`", name)
            raise
        return False


def get_task_files(task_id: int, directory: typing.Literal["input", "output"]) -> list[tuple[str, str]]:
    result_prefix = str(task_id) + "_"
    target_directory = options.INPUT_DIR if directory == "input" else os.path.join(options.OUTPUT_DIR, "visionatrix")
    r = []
    for filename in sorted(os.listdir(target_directory)):
        if filename.startswith(result_prefix):
            r.append((filename, os.path.join(target_directory, filename)))
    return r


def remove_task_files(task_id: int, directories: list[str]) -> None:
    for directory in directories:
        result_prefix = f"{task_id}_"
        if directory == "input":
            target_directory = options.INPUT_DIR
        elif directory == "output":
            target_directory = os.path.join(options.OUTPUT_DIR, "visionatrix")
        else:
            raise ValueError(f"Invalid input value: {directory}")
        for filename in os.listdir(target_directory):
            if filename.startswith(result_prefix):
                with contextlib.suppress(FileNotFoundError):
                    os.remove(os.path.join(target_directory, filename))


async def remove_task_lock(task_id: int) -> None:
    if options.VIX_MODE == "WORKER" and options.VIX_SERVER:
        return await remove_task_lock_server(task_id)
    return await remove_task_lock_database(task_id)


async def remove_task_lock_database(task_id: int) -> None:
    async with database.SESSION() as session:
        try:
            result = await session.execute(delete(database.TaskLock).where(database.TaskLock.task_id == task_id))
            if result.rowcount > 0:
                await session.commit()
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Task %s: failed to remove task lock: %s", task_id, e)


async def remove_task_lock_server(task_id: int) -> None:
    try:
        async with httpx.AsyncClient(timeout=options.WORKER_NET_TIMEOUT) as client:
            r = await client.delete(
                options.VIX_SERVER.rstrip("/") + "/vapi/tasks/lock",
                params={"task_id": task_id},
                auth=options.worker_auth(),
            )
        if httpx.codes.is_error(r.status_code):
            LOGGER.warning("Task %s: server return status: %s", task_id, r.status_code)
    except Exception as e:
        LOGGER.exception("Exception occurred: %s", e)


async def update_task_outputs(task_id: int, outputs: list[dict]) -> bool:
    async with database.SESSION() as session:
        try:
            result = await session.execute(
                update(database.TaskDetails).where(database.TaskDetails.task_id == task_id).values(outputs=outputs)
            )
            if result.rowcount == 1:
                await session.commit()
                return True
        except Exception as e:
            comfyui_wrapper.interrupt_processing()
            await session.rollback()
            LOGGER.exception("Task %s: failed to update TaskDetails outputs: %s", task_id, e)
    return False


async def update_task_progress(task_details: dict) -> bool:
    __update_temporary_execution_time(task_details)
    execution_details = task_details.get("execution_details") if task_details["progress"] == 100.0 else None
    if options.VIX_MODE == "WORKER" and options.VIX_SERVER:
        return await update_task_progress_server(task_details, execution_details)
    r = await update_task_progress_database(
        task_details["task_id"],
        task_details["progress"],
        task_details["error"],
        task_details["execution_time"],
        database.DEFAULT_USER.user_id,
        WorkerDetailsRequest.model_validate(comfyui_wrapper.get_worker_details()),
        ExecutionDetails.model_validate(execution_details) if execution_details else None,
    )
    if r and task_details["webhook_url"]:
        await webhook_task_progress(
            task_details["webhook_url"],
            task_details["webhook_headers"],
            task_details["task_id"],
            task_details["progress"],
            task_details["execution_time"],
            task_details["error"],
        )
    return r


async def update_task_progress_database(
    task_id: int,
    progress: float,
    error: str,
    execution_time: float,
    worker_user_or_id: str,
    worker_details: WorkerDetailsRequest | None,
    execution_details: ExecutionDetails | None = None,
) -> bool:
    async with database.SESSION() as session:
        try:
            if worker_details:
                worker_id, _, worker_info_values = prepare_worker_info_update(worker_user_or_id, worker_details)
            else:
                worker_id = worker_user_or_id
                worker_info_values = {}
            update_values = {
                "progress": progress,
                "error": error,
                "execution_time": execution_time,
                "updated_at": datetime.now(timezone.utc),
                "worker_id": worker_id,
            }
            if progress == 100.0:
                update_values["finished_at"] = datetime.now(timezone.utc)
                if execution_details is not None:
                    update_values["execution_details"] = execution_details.model_dump(mode="json", exclude_none=True)
            result = await session.execute(
                update(database.TaskDetails).where(database.TaskDetails.task_id == task_id).values(**update_values)
            )
            await session.commit()
            if (task_updated := result.rowcount == 1) is True and worker_info_values:
                await session.execute(
                    update(database.Worker).where(database.Worker.worker_id == worker_id).values(**worker_info_values)
                )
                await session.commit()
            return task_updated
        except Exception as e:
            comfyui_wrapper.interrupt_processing()
            await session.rollback()
            LOGGER.exception("Task %s: failed to update TaskDetails: %s", task_id, e)
    return False


async def update_task_progress_server(task_details: dict, execution_details: dict | None = None) -> bool:
    task_id = task_details["task_id"]
    request_data = {
        "worker_details": comfyui_wrapper.get_worker_details(),
        "task_id": task_id,
        "progress": task_details["progress"],
        "execution_time": task_details["execution_time"],
        "error": task_details["error"],
    }
    if execution_details is not None:
        request_data["execution_details"] = execution_details
    for i in range(3):
        try:
            async with httpx.AsyncClient(timeout=options.WORKER_NET_TIMEOUT) as client:
                r = await client.put(
                    options.VIX_SERVER.rstrip("/") + "/vapi/tasks/progress",
                    json=request_data,
                    auth=options.worker_auth(),
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


async def remove_active_task_lock():
    if ACTIVE_TASK:
        await remove_task_lock(ACTIVE_TASK["task_id"])


async def init_active_task_inputs_from_server() -> bool:
    if not (options.VIX_MODE == "WORKER" and options.VIX_SERVER):
        return True
    task_id = ACTIVE_TASK["task_id"]
    remove_task_files(task_id, ["output", "input"])
    try:
        for i, _ in enumerate(ACTIVE_TASK["input_files"]):
            for k in range(3):
                try:
                    async with httpx.AsyncClient(timeout=options.WORKER_NET_TIMEOUT) as client:
                        r = await client.get(
                            options.VIX_SERVER.rstrip("/") + "/vapi/tasks/inputs",
                            params={"task_id": task_id, "input_index": i},
                            auth=options.worker_auth(),
                        )
                        if r.status_code == httpx.codes.NOT_FOUND:
                            raise RuntimeError(f"Task {task_id}: not found on server")
                        if httpx.codes.is_error(r.status_code):
                            raise RuntimeError(f"Task {task_id}: can not get input file, status={r.status_code}")
                        with builtins.open(
                            os.path.join(options.INPUT_DIR, ACTIVE_TASK["input_files"][i]["file_name"]), mode="wb"
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
        await update_task_progress(ACTIVE_TASK)
        remove_task_files(task_id, ["output", "input"])
        await remove_task_lock(task_id)
        return False


async def upload_results_to_server(task_details: dict) -> bool:
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
        await update_task_outputs(task_id, task_details["outputs"])
        return True
    files = []
    try:
        with contextlib.ExitStack() as stack:
            for output_file in output_files:
                files.append(
                    ("files", (output_file[0], stack.enter_context(builtins.open(output_file[1], "rb")))),
                )
            try:
                for i in range(3):
                    try:
                        async with httpx.AsyncClient(timeout=options.WORKER_NET_TIMEOUT) as client:
                            r = await client.put(
                                options.VIX_SERVER.rstrip("/") + "/vapi/tasks/results",
                                params={
                                    "task_id": task_id,
                                },
                                files=files,
                                auth=options.worker_auth(),
                            )
                        if r.status_code == httpx.codes.NOT_FOUND:
                            return False
                        if not httpx.codes.is_error(r.status_code):
                            return True
                        LOGGER.error("Task %s: server return status: %s", task_id, r.status_code)
                    except (httpx.TimeoutException, httpx.RemoteProtocolError):
                        if i != 2:
                            LOGGER.warning(
                                "Task %s: attempt number %s: timeout or protocol exception occurred", task_id, i
                            )
                            continue
                        LOGGER.error(
                            "Task %s: attempt number %s: timeout or protocol exception occurred, task failed.",
                            task_id,
                            i,
                        )
            except Exception as e:
                LOGGER.exception("Task %s: exception occurred: %s", task_id, e)
    finally:
        remove_task_files(task_id, ["output", "input"])
    return False


def increase_current_task_progress(percent_finished: float) -> None:
    ACTIVE_TASK["progress"] = min(ACTIVE_TASK["progress"] + percent_finished, 99.0)


def task_progress_callback(event: str, data: dict | tuple, broadcast: bool = False):
    global ACTIVE_TASK
    LOGGER.debug("%s(broadcast=%s): %s", event, broadcast, data)
    if not isinstance(data, dict) or not data.get("prompt_id", "").startswith("vix-"):
        return

    task_id = data["prompt_id"][4:]
    if not ACTIVE_TASK:
        LOGGER.warning("ACTIVE_TASK is empty, event = %s, task_id = %s.", event, task_id)
        return

    if event == "execution_start":
        ACTIVE_TASK["execution_start_time"] = time.perf_counter()
        threading.Thread(target=update_task_progress_thread, args=(ACTIVE_TASK,), daemon=True).start()

    node_percent = 99 / ACTIVE_TASK["nodes_count"]

    nodes_execution_profiler(ACTIVE_TASK, event, data)
    if event == "executing":
        if data["node"] is None:
            ACTIVE_TASK = {}
            return
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
    elif event == "execution_success":
        current_time = time.perf_counter()
        ACTIVE_TASK["execution_time"] = current_time - ACTIVE_TASK["execution_start_time"]
        ACTIVE_TASK["progress"] = 100.0


def background_prompt_executor(prompt_executor_args: tuple | list, exit_event: threading.Event):
    global ACTIVE_TASK
    reply_count_no_tasks = 0
    last_task_name = ""

    threading.Thread(
        target=comfyui_wrapper.background_prompt_executor_comfy, args=(prompt_executor_args, exit_event), daemon=True
    ).start()

    q = prompt_executor_args[0]
    prompt_server = prompt_executor_args[1]

    while True:
        if exit_event.wait(
            min(
                options.MIN_PAUSE_INTERVAL + reply_count_no_tasks * options.MAX_PAUSE_INTERVAL / 10,
                options.MAX_PAUSE_INTERVAL,
            ),
        ):
            break

        if not ACTIVE_TASK and not q.queue:
            # ComfyUI queue is empty, can ask for a task from Visionatrix DB/Server
            ACTIVE_TASK = asyncio.run(get_incomplete_task_without_error(last_task_name))
            if not ACTIVE_TASK:
                reply_count_no_tasks = min(reply_count_no_tasks + 1, 10)
                continue

            if asyncio.run(init_active_task_inputs_from_server()) is False:
                ACTIVE_TASK = {}
                continue

            last_task_name = ACTIVE_TASK["name"]
            ACTIVE_TASK["execution_details"] = comfyui_wrapper.get_engine_details()
            ACTIVE_TASK["nodes_count"] = len(list(ACTIVE_TASK["flow_comfy"].keys()))
            ACTIVE_TASK["current_node"] = ""

            json_data = {
                "prompt": ACTIVE_TASK["flow_comfy"],
                "client_id": "visionatrix",
            }
            json_data = prompt_server.trigger_on_prompt(json_data)

            extra_data = {}
            if "extra_data" in json_data:
                extra_data = json_data["extra_data"]

            if "client_id" in json_data:
                extra_data["client_id"] = json_data["client_id"]

            if ACTIVE_TASK.get("extra_flags") and ACTIVE_TASK["extra_flags"].get("unload_models"):
                LOGGER.info("unload_models=True, models will be unloaded before execution..")
                extra_data["unload_models"] = True

            prompt_server.number += 1
            prompt_server.prompt_queue.put(
                (
                    prompt_server.number,
                    "vix-" + str(ACTIVE_TASK["task_id"]),
                    json_data["prompt"],
                    extra_data,
                    [str(i["comfy_node_id"]) for i in ACTIVE_TASK["outputs"]],
                )
            )


def update_task_progress_thread(active_task: dict) -> None:
    last_info = active_task.copy()
    asyncio.run(__update_task_progress_action(active_task, last_info))


async def __update_task_progress_action(active_task: dict, last_info: dict) -> None:
    try:
        while True:
            if last_info != active_task:
                last_info = active_task.copy()
                if last_info["progress"] == 100.0:
                    if await upload_results_to_server(last_info):
                        await update_task_progress(last_info)
                    break
                if not await update_task_progress(last_info):
                    active_task["interrupted"] = True
                    comfyui_wrapper.interrupt_processing()
                    break
                if last_info["error"]:
                    break
                active_task["execution_time"] = last_info["execution_time"]
            else:
                await asyncio.sleep(0.1)
    finally:
        await remove_task_lock(last_info["task_id"])
