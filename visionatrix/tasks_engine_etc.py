from datetime import datetime, timezone

from sqlalchemy import Row, desc, select

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
    database.TaskDetails.translated_prompt,
]


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
        },
    )


def get_get_incomplete_task_without_error_query(
    tasks_to_ask: list[str],
    tasks_to_give: list[str],
    last_task_name: str,
    user_id: str | None = None,
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
    if tasks_to_give:
        query = query.filter(database.TaskDetails.name.in_(tasks_to_give))
    if user_id is not None:
        query = query.filter(database.TaskDetails.user_id == user_id)
    if last_task_name and last_task_name in tasks_to_ask:
        query = query.order_by(desc(database.TaskDetails.priority), desc(database.TaskDetails.name == last_task_name))
    else:
        query = query.order_by(desc(database.TaskDetails.priority))
    return query
