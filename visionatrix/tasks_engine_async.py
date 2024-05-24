import asyncio
import logging
import threading
import typing
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from . import database, options
from .comfyui import interrupt_processing
from .pydantic_models import (
    TaskDetails,
    TaskDetailsShort,
    UserInfo,
    WorkerDetails,
    WorkerDetailsRequest,
)
from .tasks_engine import (
    __get_get_incomplete_task_without_error_query,
    __get_task_query,
    __get_tasks_query,
    __get_worker_query,
    __get_workers_query,
    __init_new_task_details,
    __lock_task_and_return_details,
    __prepare_worker_info_update,
    __task_details_from_dict,
    __task_details_short_to_dict,
    __task_details_to_dict,
    background_prompt_executor,
    remove_task_files,
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
    return __init_new_task_details(new_task_queue.id, name, input_params, user_info)


async def put_task_in_queue_async(task_details: dict) -> None:
    LOGGER.debug("Put flow in queue: %s", task_details)
    async with database.SESSION_ASYNC() as session:
        try:
            session.add(__task_details_from_dict(task_details))
            await session.commit()
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to put task in queue: %s", task_details["task_id"])
            remove_task_files(task_details["task_id"], ["input"])
            raise


async def get_task_async(task_id: int, user_id: str | None = None) -> dict | None:
    async with database.SESSION_ASYNC() as session:
        try:
            query = __get_task_query(task_id, user_id)
            task = (await session.execute(query)).one_or_none()
            return __task_details_to_dict(task) if task else None
        except Exception:
            LOGGER.exception("Failed to retrieve task: %s", task_id)
            raise


async def get_tasks_async(
    name: str | None = None,
    finished: bool | None = None,
    user_id: str | None = None,
) -> dict[int, TaskDetails]:
    async with database.SESSION_ASYNC() as session:
        try:
            query = __get_tasks_query(name, finished, user_id)
            results = (await session.execute(query)).all()
            return {task.task_id: TaskDetails.model_validate(__task_details_to_dict(task)) for task in results}
        except Exception:
            LOGGER.exception("Failed to retrieve tasks: `%s`, finished=%s", name, finished)
            raise


async def get_tasks_short_async(
    user_id: str,
    name: str | None = None,
    finished: bool | None = None,
) -> dict[int, TaskDetailsShort]:
    async with database.SESSION_ASYNC() as session:
        try:
            query = __get_tasks_query(name, finished, user_id, full_info=False)
            results = (await session.execute(query)).all()
            return {
                task.task_id: TaskDetailsShort.model_validate(__task_details_short_to_dict(task)) for task in results
            }
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
            worker_id, worker_device_name, worker_info_values = __prepare_worker_info_update(
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
                query = session.query(database.Worker).filter(database.Worker.worker_id == worker_id)
                tasks_to_give = await query.first().tasks_to_give
            query = __get_get_incomplete_task_without_error_query(
                session, tasks_to_ask, tasks_to_give, last_task_name, user_id
            )
            task = await query.first()
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
            worker_id, _, worker_info_values = __prepare_worker_info_update(worker_user_id, worker_details)
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


async def get_workers_details_async(
    user_id: str | None, last_seen_interval: int, worker_id: str
) -> list[WorkerDetails]:
    async with database.SESSION_ASYNC() as session:
        try:
            query = __get_workers_query(user_id, last_seen_interval, worker_id)
            results = (await session.execute(query)).scalars().all()
            return [WorkerDetails.model_validate(i) for i in results]
        except Exception:
            LOGGER.exception("Failed to retrieve workers: `%s`, %s, %s", user_id, last_seen_interval, worker_id)
            raise


async def get_worker_details_from_db_async(user_id: str | None, worker_id: str) -> WorkerDetails | None:
    async with database.SESSION_ASYNC() as session:
        try:
            query = __get_worker_query(user_id, worker_id)
            result = (await session.execute(query)).scalars().one_or_none()
            return None if result is None else WorkerDetails.model_validate(result)
        except Exception:
            LOGGER.exception("Failed to retrieve worker: `%s`, %s", user_id, worker_id)
            raise


async def set_worker_tasks_to_give_db_async(user_id: str | None, worker_id: str, tasks_to_give: list[str]) -> bool:
    async with database.SESSION_ASYNC() as session:
        try:
            query = update(database.Worker).where(database.Worker.worker_id == worker_id)
            if user_id is not None:
                query = query.where(database.Worker.user_id == user_id)
            result = session.execute(query.values(tasks_to_give=tasks_to_give))
            await session.commit()
            return result.rowcount > 0
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to update tasks for worker(`%s`, `%s`): %s", user_id, worker_id, e)
            return False
