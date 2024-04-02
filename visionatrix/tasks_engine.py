import asyncio
import contextlib
import gc
import logging
import os
import time
import typing
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    and_,
    create_engine,
    delete,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from . import options
from .comfyui import cleanup_models, interrupt_processing, soft_empty_cache

Base = declarative_base()


class TaskQueue(Base):
    __tablename__ = "tasks_queue"
    id = Column(Integer, primary_key=True, autoincrement=True)


class TaskDetails(Base):
    __tablename__ = "tasks_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks_queue.id"), nullable=False, unique=True)
    progress = Column(Float, default=0.0)
    error = Column(String, default="")
    name = Column(String, default="")
    input_params = Column(JSON, default={})
    outputs = Column(JSON, default=[])
    input_files = Column(JSON, default=[])
    flow_comfy = Column(JSON, default={})
    task_queue = relationship("TaskQueue")


class TaskLock(Base):
    __tablename__ = "task_locks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks_queue.id"), nullable=False, unique=True)
    locked_at = Column(DateTime, default=datetime.utcnow)
    task_queue = relationship("TaskQueue", backref="lock")


LOGGER = logging.getLogger("visionatrix")
DB_SESSION_MAKER: sessionmaker
TASKS_FILES_DIR: str
ACTIVE_TASK: dict


def create_new_task(name: str, input_params: dict) -> dict:
    session = DB_SESSION_MAKER()
    try:
        new_task_queue = TaskQueue()
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
        }
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to add to TaskQueue: %s", e)
        raise
    finally:
        session.close()


def put_task_in_queue(task_details: dict) -> None:
    LOGGER.debug("Put flow in queue: %s", task_details)
    session = DB_SESSION_MAKER()
    try:
        new_task = TaskDetails(
            task_id=task_details["task_id"],
            name=task_details["name"],
            input_params=task_details["input_params"],
            progress=task_details["progress"],
            error=task_details["error"],
            outputs=task_details["outputs"],
            input_files=task_details["input_files"],
            flow_comfy=task_details["flow_comfy"],
        )
        session.add(new_task)
        session.commit()
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to add task: %s", e)
        remove_task_files(task_details["task_id"], ["input"])
        raise
    finally:
        session.close()


def get_task(task_id: int) -> dict | None:
    session = DB_SESSION_MAKER()
    try:
        task = session.query(TaskDetails).filter(TaskDetails.task_id == task_id).first()
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
        }
    except Exception as e:
        LOGGER.exception("Failed to retrieve task: %s", e)
        raise
    finally:
        session.close()


def get_incomplete_task_without_error() -> dict:
    session = DB_SESSION_MAKER()
    try:
        task = (
            session.query(TaskDetails)
            .outerjoin(TaskLock, TaskDetails.task_id == TaskLock.task_id)
            .filter(TaskDetails.error == "", TaskDetails.progress != 100.0, TaskLock.id.is_(None))
            .first()
        )
        if not task:
            return {}
        try:
            lock = TaskLock(task_id=task.task_id, locked_at=datetime.utcnow())
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
        }
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to retrieve task without error and incomplete progress: %s", e)
        return {}
    finally:
        session.close()


def get_tasks(name: str | None = None, finished: bool | None = None) -> dict:
    session = DB_SESSION_MAKER()
    try:
        query = session.query(TaskDetails)
        if name is not None:
            query = query.filter(TaskDetails.name == name)
        if finished is not None:
            if finished:
                query = query.filter(TaskDetails.progress == 100.0)
            else:
                query = query.filter(TaskDetails.progress < 100.0)
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
            }
            for task in tasks
        }
    except Exception as e:
        LOGGER.exception("Failed to retrieve tasks: %s", e)
        raise
    finally:
        session.close()


def remove_task_by_id(task_id: int) -> bool:
    session = DB_SESSION_MAKER()
    try:
        lock_result = session.execute(delete(TaskLock).where(TaskLock.task_id == task_id))
        details_result = session.execute(delete(TaskDetails).where(TaskDetails.task_id == task_id))
        if lock_result.rowcount + details_result.rowcount > 0:
            session.commit()
            return True
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to remove task: %s", e)
        raise
    finally:
        session.close()
        remove_task_files(task_id, ["output", "input"])
    return False


def remove_task_by_name(name: str) -> None:
    tasks_to_delete = get_tasks(name=name, finished=True)
    session = DB_SESSION_MAKER()
    try:
        for task_id in tasks_to_delete:
            session.execute(delete(TaskLock).where(TaskLock.task_id == task_id))
            session.execute(delete(TaskDetails).where(TaskDetails.task_id == task_id))
            session.commit()
            remove_task_files(task_id, ["output", "input"])
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to remove task by name '%s': %s", name, e)
        raise
    finally:
        session.close()


def remove_unfinished_task_by_id(task_id: int) -> bool:
    session = DB_SESSION_MAKER()
    try:
        session.execute(delete(TaskLock).where(TaskLock.task_id == task_id))
        details_result = session.execute(
            delete(TaskDetails).where(and_(TaskDetails.progress != 100.0, TaskDetails.task_id == task_id))
        )
        if details_result.rowcount > 0:
            session.commit()
            remove_task_files(task_id, ["output", "input"])
            return True
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to remove task: %s", e)
        raise
    finally:
        session.close()
    return False


def remove_unfinished_tasks_by_name(name: str) -> bool:
    session = DB_SESSION_MAKER()
    try:
        stmt = delete(TaskDetails).where(and_(TaskDetails.progress != 100.0, TaskDetails.name == name))
        result = session.execute(stmt)
        if result.rowcount > 0:
            session.commit()
            return True
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to remove incomplete TaskDetails: %s", e)
        raise
    finally:
        session.close()
    return False


def remove_task_files(task_id: int, directories: list[str]) -> None:
    for directory in directories:
        result_prefix = f"{task_id}_"
        target_directory = os.path.join(TASKS_FILES_DIR, directory)
        for filename in os.listdir(target_directory):
            if filename.startswith(result_prefix):
                with contextlib.suppress(FileNotFoundError):
                    os.remove(os.path.join(target_directory, filename))


def remove_task_lock(task_id: int) -> None:
    session = DB_SESSION_MAKER()
    try:
        result = session.execute(delete(TaskLock).where(TaskLock.task_id == task_id))
        if result.rowcount > 0:
            session.commit()
    except Exception as e:
        session.rollback()
        LOGGER.exception("Failed to remove task lock for task_id %s: %s", task_id, e)
    finally:
        session.close()


def update_task_progress(task_details: dict) -> bool:
    session = DB_SESSION_MAKER()
    try:
        result = session.execute(
            update(TaskDetails)
            .where(TaskDetails.task_id == task_details["task_id"])
            .values(progress=task_details["progress"], error=task_details["error"])
        )
        session.commit()
        return result.rowcount == 1
    except Exception as e:
        interrupt_processing()
        session.rollback()
        LOGGER.exception("Task %s failed to update TaskDetails: %s", task_details["task_id"], e)
    finally:
        session.close()
    return False


def increase_current_task_progress(percent_finished: float) -> None:
    ACTIVE_TASK["progress"] = min(ACTIVE_TASK["progress"] + percent_finished, 99.0)


def task_progress_callback(event: str, data: dict, broadcast: bool = False):
    LOGGER.debug("%s(broadcast=%s): %s", event, broadcast, data)
    if not ACTIVE_TASK:
        LOGGER.warning("CurrentTaskDetails is empty, event = %s.", event)
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

        ACTIVE_TASK = get_incomplete_task_without_error()
        if not ACTIVE_TASK:
            time.sleep(0.1)
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
            update_task_progress(ACTIVE_TASK)
            remove_task_lock(ACTIVE_TASK["task_id"])
        ACTIVE_TASK = {}
        LOGGER.info("Prompt executed in %f seconds", current_time - execution_start_time)
        need_gc = True


async def start_tasks_engine(tasks_files_dir: str, comfy_queue: typing.Any, exit_event: asyncio.Event) -> None:
    global TASKS_FILES_DIR

    async def start_background_tasks_engine(prompt_executor):
        await asyncio.to_thread(background_prompt_executor, prompt_executor, exit_event)

    TASKS_FILES_DIR = tasks_files_dir
    init_database_engine()
    _ = asyncio.create_task(start_background_tasks_engine(comfy_queue))  # noqa


def init_database_engine() -> None:
    global DB_SESSION_MAKER

    connect_args = {}
    database_uri = options.DATABASE_URI
    if database_uri.startswith("sqlite:"):
        connect_args = {"check_same_thread": False}
        if database_uri.startswith("sqlite:///."):
            database_uri = f"sqlite:///{os.path.abspath(os.path.join(TASKS_FILES_DIR, database_uri[10:]))}"
    engine = create_engine(database_uri, connect_args=connect_args)
    Base.metadata.create_all(engine)
    DB_SESSION_MAKER = sessionmaker(autocommit=False, autoflush=False, bind=engine)
