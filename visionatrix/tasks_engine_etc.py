import logging
import time
from datetime import datetime, timezone

from sqlalchemy import Row, desc, or_, select

from . import database
from .pydantic_models import UserInfo, WorkerDetailsRequest

TASK_DETAILS_COLUMNS_SHORT = [
    database.TaskDetails.task_id,
    database.TaskDetails.name,
    database.TaskDetails.priority,
    database.TaskDetails.progress,
    database.TaskDetails.error,
    database.TaskDetails.execution_time,
    database.TaskDetails.group_scope,
    database.TaskDetails.input_params,
    database.TaskDetails.input_files,
    database.TaskDetails.outputs,
    database.TaskLock.locked_at,
    database.TaskDetails.worker_id,
    database.TaskDetails.parent_task_id,
    database.TaskDetails.parent_task_node_id,
    database.TaskDetails.translated_input_params,
    database.TaskDetails.extra_flags,
    database.TaskDetails.hidden,
]

TASK_DETAILS_COLUMNS = [
    *TASK_DETAILS_COLUMNS_SHORT,
    database.TaskDetails.flow_comfy,
    database.TaskDetails.user_id,
    database.TaskDetails.created_at,
    database.TaskDetails.updated_at,
    database.TaskDetails.finished_at,
    database.TaskDetails.webhook_url,
    database.TaskDetails.webhook_headers,
    database.TaskDetails.execution_details,
    database.TaskDetails.custom_worker,
]

LOGGER = logging.getLogger("visionatrix")


def init_new_task_details(task_id: int, name: str, input_params: dict, user_info: UserInfo) -> dict:
    return {
        "task_id": task_id,
        "name": name,
        "input_params": input_params,
        "progress": 0.0,
        "error": "",
        "outputs": [],
        "input_files": [],
        "flow_comfy": {},
        "user_id": user_info.user_id,
        "execution_time": 0.0,
    }


def task_details_from_dict(task_details: dict) -> database.TaskDetails:
    return database.TaskDetails(
        task_id=task_details["task_id"],
        name=task_details["name"],
        input_params=task_details["input_params"],
        priority=task_details["priority"],
        progress=task_details["progress"],
        error=task_details["error"],
        outputs=task_details["outputs"],
        input_files=task_details["input_files"],
        flow_comfy=task_details["flow_comfy"],
        user_id=task_details["user_id"],
        created_at=task_details.get("created_at"),
        updated_at=task_details.get("updated_at"),
        finished_at=task_details.get("finished_at"),
        execution_time=task_details["execution_time"],
        group_scope=task_details["group_scope"],
        webhook_url=task_details.get("webhook_url"),
        webhook_headers=task_details.get("webhook_headers"),
        parent_task_id=task_details.get("parent_task_id"),
        parent_task_node_id=task_details.get("parent_task_node_id"),
        translated_input_params=task_details.get("translated_input_params"),
        extra_flags=task_details.get("extra_flags"),
        custom_worker=task_details.get("custom_worker"),
        hidden=task_details.get("hidden"),
    )


def task_details_to_dict(task_details: Row) -> dict:
    r = task_details_short_to_dict(task_details)
    r.update(
        {
            "task_id": task_details.task_id,
            "flow_comfy": task_details.flow_comfy,
            "user_id": task_details.user_id,
            "created_at": task_details.created_at,
            "updated_at": task_details.updated_at,
            "finished_at": task_details.finished_at,
            "webhook_url": task_details.webhook_url,
            "webhook_headers": task_details.webhook_headers,
            "execution_details": task_details.execution_details,
            "custom_worker": task_details.custom_worker,
        }
    )
    return r


def task_details_short_to_dict(task_details: Row) -> dict:
    return {
        "task_id": task_details.task_id,
        "priority": task_details.priority,
        "progress": task_details.progress,
        "error": task_details.error,
        "name": task_details.name,
        "input_params": task_details.input_params,
        "outputs": task_details.outputs,
        "input_files": task_details.input_files,
        "execution_time": task_details.execution_time,
        "group_scope": task_details.group_scope,
        "locked_at": task_details.locked_at,
        "worker_id": task_details.worker_id,
        "parent_task_id": task_details.parent_task_id,
        "parent_task_node_id": task_details.parent_task_node_id,
        "child_tasks": [],
        "translated_input_params": task_details.translated_input_params,
        "extra_flags": task_details.extra_flags,
        "hidden": task_details.hidden,
    }


def prepare_worker_info_update(worker_user_id: str, worker_details: WorkerDetailsRequest) -> tuple[str, str, dict]:
    worker_device = worker_details.devices[0]
    return (
        f"{worker_user_id}:{worker_details.system.hostname}:[{worker_device.name}]:{worker_device.index}",
        worker_device.name,
        {
            "worker_version": worker_details.worker_version,
            "pytorch_version": worker_details.pytorch_version,
            "os": worker_details.system.os,
            "version": worker_details.system.version,
            "embedded_python": worker_details.system.embedded_python,
            "device_type": worker_device.type,
            "vram_total": worker_device.vram_total,
            "vram_free": worker_device.vram_free,
            "torch_vram_total": worker_device.torch_vram_total,
            "torch_vram_free": worker_device.torch_vram_free,
            "ram_total": worker_details.ram_total,
            "ram_free": worker_details.ram_free,
            "last_seen": datetime.now(timezone.utc),
            "engine_details": worker_details.engine_details.model_dump(mode="json"),
        },
    )


def get_get_incomplete_task_without_error_query(
    tasks_to_ask: list[str],
    tasks_to_give: list[str],
    last_task_name: str,
    worker_id: str,
    user_id: str | None,
):
    query = select(database.TaskDetails).outerjoin(
        database.TaskLock, database.TaskDetails.task_id == database.TaskLock.task_id
    )
    query = query.filter(
        database.TaskDetails.error == "",
        database.TaskDetails.progress != 100.0,
        database.TaskLock.id.is_(None),
        database.TaskDetails.name.in_(tasks_to_ask),
    )
    query = query.filter(
        or_(
            database.TaskDetails.custom_worker.is_(None),
            database.TaskDetails.custom_worker == worker_id,
        )
    )
    if tasks_to_give:
        query = query.filter(database.TaskDetails.name.in_(tasks_to_give))
    if user_id is not None:
        query = query.filter(database.TaskDetails.user_id == user_id)
    if last_task_name and last_task_name in tasks_to_ask:
        query = query.order_by(desc(database.TaskDetails.priority), desc(database.TaskDetails.name == last_task_name))
    else:
        query = query.order_by(desc(database.TaskDetails.priority))
    return query


def nodes_execution_profiler(active_task: dict, event: str, data: dict):
    try:
        __nodes_execution_profiler(active_task, event, data)
    except Exception as e:
        LOGGER.exception("Unexpected error in Profiler for task: %s", e)


def __nodes_execution_profiler(active_task: dict, event: str, data: dict):
    if active_task.get("extra_flags") is None or not active_task.get("extra_flags").get("profiler_execution"):
        return

    if event not in ("executing", "execution_start", "execution_success", "execution_cached"):
        return

    if event == "execution_start":  # triggered only once for each task at the beginning
        active_task["execution_details"].update(
            {
                "nodes_profiling": [],
                "max_memory_usage": 0.0,
            }
        )
        return

    if event == "execution_cached":
        for node_id in data.get("nodes", []):
            cached_node_info = active_task["flow_comfy"].get(node_id)
            if not cached_node_info:
                LOGGER.warning("Node with id='%s' for profiling was not found in flow_comfy.", node_id)
                continue
            profiling_data = {
                "execution_time": 0.0,
                "gpu_memory_usage": 0.0,
                "class_type": cached_node_info.get("class_type", ""),
                "title": cached_node_info.get("_meta", {}).get("title", ""),
                "node_id": node_id,
            }
            active_task["execution_details"]["nodes_profiling"].append(profiling_data)

    last_active_node = active_task.get("profiler_current_node")
    current_node = data.get("node")

    if event != "execution_success" and last_active_node == current_node:
        LOGGER.debug("Node '%s' profiling was already initiated, skipping.", last_active_node)
        return

    import torch  # noqa

    # here we have an "execute" event that fires at the start of each node's execution
    if last_active_node and last_active_node != current_node:
        execution_time = time.perf_counter() - active_task["profiler_node_start_time"]
        gpu_memory_usage = round(torch.cuda.max_memory_allocated() / 1024**2, 2) if torch.cuda.is_available() else 0.0

        node_info = active_task["flow_comfy"].get(last_active_node)
        if not node_info:
            LOGGER.warning("Node with id='%s' for profiling was not found in flow_comfy.", last_active_node)
            return

        profiling_data = {
            "execution_time": execution_time,
            "gpu_memory_usage": gpu_memory_usage,
            "class_type": node_info.get("class_type", ""),
            "title": node_info.get("_meta", {}).get("title", ""),
            "node_id": last_active_node,
        }
        active_task["execution_details"]["nodes_profiling"].append(profiling_data)

    if event == "execution_success":
        if active_task["execution_details"]["nodes_profiling"]:
            active_task["execution_details"]["max_memory_usage"] = max(
                i["gpu_memory_usage"] for i in active_task["execution_details"]["nodes_profiling"]
            )
            active_task["execution_details"]["nodes_execution_time"] = sum(
                i["execution_time"] for i in active_task["execution_details"]["nodes_profiling"]
            )
        else:
            active_task["execution_details"]["max_memory_usage"] = 0.0
            active_task["execution_details"]["nodes_execution_time"] = 0.0
        active_task.pop("profiler_current_node", None)
        active_task.pop("profiler_node_start_time", None)
        return

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    active_task["profiler_current_node"] = current_node
    active_task["profiler_node_start_time"] = time.perf_counter()
