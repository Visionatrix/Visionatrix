import asyncio
import logging
import threading
import typing
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from . import database, options
from .comfyui import interrupt_processing
from .pydantic_models import (
    TaskDetails,
    TaskDetailsShort,
    UserInfo,
    WorkerDetailsRequest,
)
from .tasks_engine import (
    __get_task_query,
    __get_tasks_query,
    __lock_task_and_return_details,
    background_prompt_executor,
    remove_task_files,
)
from .tasks_engine_etc import (
    TASK_DETAILS_COLUMNS_SHORT,
    get_get_incomplete_task_without_error_query,
    init_new_task_details,
    prepare_worker_info_update,
    task_details_from_dict,
    task_details_short_to_dict,
    task_details_to_dict,
)

LOGGER = logging.getLogger("visionatrix")


async def create_new_task_async(name: str, input_params: dict, user_info: UserInfo) -> dict:
    async with database.SESSION_ASYNC() as session:
        try:
            new_task_queue = database.TaskQueue()
            session.add(new_task_queue)
            await session.commit()
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to add `%s` to TaskQueue(%s)", name, user_info.user_id)
            raise
    remove_task_files(new_task_queue.id, ["output", "input"])
    return init_new_task_details(new_task_queue.id, name, input_params, user_info)


async def put_task_in_queue_async(task_details: dict) -> None:
    LOGGER.debug("Put flow in queue: %s", task_details)
    async with database.SESSION_ASYNC() as session:
        try:
            session.add(task_details_from_dict(task_details))
            await session.commit()
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to put task in queue: %s", task_details["task_id"])
            remove_task_files(task_details["task_id"], ["input"])
            raise


async def fetch_child_tasks_async(session, parent_task_ids: list[int]) -> dict[int, list[TaskDetailsShort]]:
    if not parent_task_ids:
        return {}

    query = (
        select(*TASK_DETAILS_COLUMNS_SHORT)
        .outerjoin(database.TaskLock, database.TaskLock.task_id == database.TaskDetails.task_id)
        .filter(database.TaskDetails.parent_task_id.in_(parent_task_ids))
    )
    child_tasks = (await session.execute(query)).all()

    parent_to_children = {}
    for task in child_tasks:
        task_details = task_details_short_to_dict(task)
        parent_to_children.setdefault(task.parent_task_id, []).append(task_details)

    next_level_parent_ids = [task.task_id for task in child_tasks]
    next_level_children = await fetch_child_tasks_async(session, next_level_parent_ids)
    for children in parent_to_children.values():
        for child in children:
            child["child_tasks"] = next_level_children.get(child["task_id"], [])
    return parent_to_children


async def get_task_async(task_id: int, user_id: str | None = None, fetch_child: bool = False) -> dict | None:
    async with database.SESSION_ASYNC() as session:
        try:
            query = __get_task_query(task_id, user_id)
            task = (await session.execute(query)).one_or_none()
            if task:
                task_dict = task_details_to_dict(task)
                if fetch_child:
                    child_tasks = await fetch_child_tasks_async(session, [task.task_id])
                    task_dict["child_tasks"] = child_tasks.get(task.task_id, [])
                return task_dict
            return None
        except Exception:
            LOGGER.exception("Failed to retrieve task: %s", task_id)
            raise


async def get_tasks_async(
    name: str | None = None,
    group_scope: int = 1,
    finished: bool | None = None,
    user_id: str | None = None,
    fetch_child: bool = False,
    only_parent: bool = False,
) -> dict[int, TaskDetails]:
    async with database.SESSION_ASYNC() as session:
        try:
            query = __get_tasks_query(name, group_scope, finished, user_id, only_parent=only_parent)
            results = (await session.execute(query)).all()
            tasks = {}
            task_ids = [task.task_id for task in results]
            child_tasks = await fetch_child_tasks_async(session, task_ids) if fetch_child else {}
            for task in results:
                task_details = task_details_to_dict(task)
                task_details["child_tasks"] = child_tasks.get(task.task_id, [])
                tasks[task.task_id] = TaskDetails.model_validate(task_details)
            return tasks
        except Exception:
            LOGGER.exception("Failed to retrieve tasks: `%s`, finished=%s", name, finished)
            raise


async def get_tasks_short_async(
    user_id: str,
    name: str | None = None,
    group_scope: int = 1,
    finished: bool | None = None,
    fetch_child: bool = False,
    only_parent: bool = False,
) -> dict[int, TaskDetailsShort]:
    async with database.SESSION_ASYNC() as session:
        try:
            query = __get_tasks_query(name, group_scope, finished, user_id, full_info=False, only_parent=only_parent)
            results = (await session.execute(query)).all()
            tasks = {}
            task_ids = [task.task_id for task in results]
            child_tasks = await fetch_child_tasks_async(session, task_ids) if fetch_child else {}
            for task in results:
                task_details = task_details_short_to_dict(task)
                task_details["child_tasks"] = child_tasks.get(task.task_id, [])
                tasks[task.task_id] = TaskDetailsShort.model_validate(task_details)
            return tasks
        except Exception:
            LOGGER.exception("Failed to retrieve tasks: `%s`, finished=%s", name, finished)
            raise


async def update_task_outputs_async(task_id: int, outputs: list[dict]) -> bool:
    async with database.SESSION_ASYNC() as session:
        try:
            result = await session.execute(
                update(database.TaskDetails).where(database.TaskDetails.task_id == task_id).values(outputs=outputs)
            )
            if result.rowcount == 1:
                await session.commit()
                return True
        except Exception as e:
            interrupt_processing()
            await session.rollback()
            LOGGER.exception("Task %s: failed to update TaskDetails outputs: %s", task_id, e)
    return False


async def get_incomplete_task_without_error_database_async(
    worker_user_id: str,
    worker_details: WorkerDetailsRequest,
    tasks_to_ask: list[str],
    last_task_name: str,
    user_id: str | None = None,
) -> dict:
    if not tasks_to_ask:
        return {}
    async with database.SESSION_ASYNC() as session:
        try:
            worker_id, worker_device_name, worker_info_values = prepare_worker_info_update(
                worker_user_id, worker_details
            )
            result = await session.execute(
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
                tasks_to_give = (await session.execute(query)).scalar().tasks_to_give
            query = get_get_incomplete_task_without_error_query(tasks_to_ask, tasks_to_give, last_task_name, user_id)
            task = (await session.execute(query)).scalar()
            if not task:
                await session.commit()
                return {}
            return await lock_task_and_return_details_async(session, task)
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to retrieve task for processing: %s", e)
            return {}
        finally:
            await session.close()


async def lock_task_and_return_details_async(session, task: type[database.TaskDetails] | database.TaskDetails) -> dict:
    try:
        session.add(database.TaskLock(task_id=task.task_id, locked_at=datetime.utcnow()))
        await session.commit()
        return __lock_task_and_return_details(task)
    except IntegrityError:
        await session.rollback()
        return {}


async def update_task_progress_database_async(
    task_id: int,
    progress: float,
    error: str,
    execution_time: float,
    worker_user_id: str,
    worker_details: WorkerDetailsRequest,
) -> bool:
    async with database.SESSION_ASYNC() as session:
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
            result = await session.execute(
                update(database.TaskDetails).where(database.TaskDetails.task_id == task_id).values(**update_values)
            )
            await session.commit()
            if (task_updated := result.rowcount == 1) is True:
                await session.execute(
                    update(database.Worker).where(database.Worker.worker_id == worker_id).values(**worker_info_values)
                )
                await session.commit()
            return task_updated
        except Exception as e:
            interrupt_processing()
            await session.rollback()
            LOGGER.exception("Task %s: failed to update TaskDetails: %s", task_id, e)
    return False


async def task_restart_database_async(task_id: int) -> bool:
    async with database.SESSION_ASYNC() as session:
        try:
            update_values = {
                "progress": 0.0,
                "error": "",
                "execution_time": 0.0,
                "updated_at": datetime.now(timezone.utc),
                "worker_id": None,
            }
            result = await session.execute(
                update(database.TaskDetails).where(database.TaskDetails.task_id == task_id).values(**update_values)
            )
            await session.commit()
            return result.rowcount == 1
        except Exception as e:
            interrupt_processing()
            await session.rollback()
            LOGGER.exception("Task %s: failed to restart: %s", task_id, e)
    return False


async def start_tasks_engine(comfy_queue: typing.Any, exit_event: threading.Event) -> None:
    async def start_background_tasks_engine(prompt_executor):
        await asyncio.to_thread(background_prompt_executor, prompt_executor, exit_event)

    database.init_database_engine()
    if options.VIX_MODE != "SERVER":
        _ = asyncio.create_task(start_background_tasks_engine(comfy_queue))  # noqa


async def update_task_info_database_async(task_id: int, update_fields: dict) -> bool:
    async with database.SESSION_ASYNC() as session:
        try:
            result = await session.execute(
                update(database.TaskDetails)
                .where(database.TaskDetails.task_id == task_id, database.TaskDetails.progress == 0.0)
                .values(**update_fields)
            )
            await session.commit()
            return result.rowcount == 1
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Task %s: failed to update task info: %s", task_id, e)
            return False
