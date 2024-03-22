import asyncio
import builtins
import contextlib
import gc
import json
import logging
import os
import threading
import time
import typing

from .comfyui import interrupt_processing, soft_empty_cache

LOGGER = logging.getLogger("visionatrix")

ACTIVE_TASK: dict = {}
TASKS_HISTORY = {}
"""{
    task_id: {
        progress: 0.0-100.0,
        error: "",
        name: "",
        input_params: "",
        outputs: [{"comfy_node_id": int, "type": str}],
        input_files: [],
        flow_comfy: {},
        interrupt: bool,
        }
    }"""
TASKS_QUEUE = {}
"""{
    task_id: {
        progress: 0.0-100.0,
        error: "",
        name: "",
        input_params: "",
        outputs: [{"comfy_node_id": int, "type": str}],
        input_files: [],
        flow_comfy: {},
        interrupt: bool,
        }
    }"""
NEXT_TASK_ID = 1
TASKS_CREATION_LOCK = threading.RLock()


def create_new_task(name: str, input_params: dict, tasks_files_dir: str) -> [int, dict]:
    global NEXT_TASK_ID  # pylint: disable=global-statement

    task_details = {
        "progress": 0.0,
        "error": "",
        "name": name,
        "input_params": input_params,
        "outputs": [],
        "input_files": [],
        "flow_comfy": {},
        "interrupt": False,
    }

    with TASKS_CREATION_LOCK:
        task_id = NEXT_TASK_ID
        NEXT_TASK_ID += 1
    remove_task_files(task_id, tasks_files_dir, ["output", "input"])
    return task_id, task_details


def put_task_in_queue(task_id: int, task_details: dict) -> None:
    TASKS_QUEUE.update({task_id: task_details})


def get_task_from_queue(task_id: int) -> dict | None:
    return TASKS_QUEUE.get(task_id)


def get_task_from_history(task_id: int) -> dict | None:
    return TASKS_HISTORY.get(task_id)


def get_task(task_id: int) -> dict | None:
    task_details = get_task_from_queue(task_id)
    if task_details is None:
        task_details = get_task_from_history(task_id)
    return task_details


def get_tasks_from_queue() -> dict:
    return TASKS_QUEUE


def get_tasks_from_history() -> dict:
    return TASKS_HISTORY


def get_tasks() -> dict:
    return get_tasks_from_queue() | get_tasks_from_history()


def remove_task(task_id: int, tasks_files_dir: str) -> None:
    task_details = TASKS_QUEUE.pop(task_id, {})
    if task_details:
        task_details["interrupt"] = True
    else:
        TASKS_HISTORY.pop(task_id, {})
    remove_task_files(task_id, tasks_files_dir, ["output", "input"])


def remove_task_files(task_id: int, tasks_files_dir: str, directories: list[str]) -> None:
    if not tasks_files_dir:
        return
    for directory in directories:
        result_prefix = f"{task_id}_"
        target_directory = os.path.join(tasks_files_dir, directory)
        for filename in os.listdir(target_directory):
            if filename.startswith(result_prefix):
                with contextlib.suppress(FileNotFoundError):
                    os.remove(os.path.join(target_directory, filename))


def save_tasks(tasks_files_dir: str) -> int:
    tasks = TASKS_QUEUE | TASKS_HISTORY
    with builtins.open(os.path.join(tasks_files_dir, "tasks_history.json"), mode="w", encoding="UTF-8") as file:
        json.dump(tasks, file)
    LOGGER.debug("saved %s tasks", len(tasks))
    return len(tasks)


def load_tasks(tasks_files_dir: str):
    global NEXT_TASK_ID  # pylint: disable=global-statement

    tasks_history = os.path.join(tasks_files_dir, "tasks_history.json")
    tasks = {}
    if os.path.exists(tasks_history):
        with builtins.open(tasks_history, mode="r", encoding="UTF-8") as file:
            tasks = json.load(file)
            tasks = {int(k): v for k, v in tasks.items()}
            for k, v in tasks.items():
                if v["error"]:  # clear from history tasks with errors
                    remove_task_files(k, tasks_files_dir, ["output", "input"])
                    continue
                if v["progress"] < 100.0:
                    v["progress"] = 0.0
                    remove_task_files(k, tasks_files_dir, ["output"])
                    TASKS_QUEUE[k] = v
                else:
                    TASKS_HISTORY[k] = v
        LOGGER.info("Loaded %s tasks", len(tasks))
    else:
        LOGGER.info("No `tasks_history.json` to load.")
    NEXT_TASK_ID = 1 + max(tasks.keys(), default=0)


def increase_current_task_progress(percent_finished: float) -> None:
    ACTIVE_TASK["progress"] = min(ACTIVE_TASK["progress"] + percent_finished, 99.9)


def task_progress_callback(event: str, data: dict, broadcast: bool = False):
    LOGGER.debug("%s(broadcast=%s): %s", event, broadcast, data)
    if not ACTIVE_TASK:
        LOGGER.warning("CurrentTaskDetails is empty, event = %s.", event)
        return
    node_percent = 100 / ACTIVE_TASK["nodes_count"]

    if ACTIVE_TASK["interrupt"] is True:
        interrupt_processing()
    elif event == "executing":
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
        increase_current_task_progress(len(data["nodes"]) * node_percent)
    elif event == "execution_interrupted":
        ACTIVE_TASK["interrupt"] = True


def background_prompt_executor(prompt_executor, exit_event: asyncio.Event):
    global ACTIVE_TASK  # pylint: disable=global-statement

    last_gc_collect = 0
    need_gc = False
    gc_collect_interval = 20.0

    while True:
        if exit_event.is_set():
            break
        if need_gc:
            current_time = time.perf_counter()
            if (current_time - last_gc_collect) > gc_collect_interval:
                LOGGER.debug("gc.collect")
                gc.collect()
                soft_empty_cache()
                last_gc_collect = current_time
                need_gc = False

        if not TASKS_QUEUE:
            time.sleep(0.05)
            continue
        task_id, ACTIVE_TASK = next(iter(TASKS_QUEUE.items()))
        ACTIVE_TASK["nodes_count"] = len(list(ACTIVE_TASK["flow_comfy"].keys()))
        ACTIVE_TASK["current_node"] = ""
        prompt_executor.server.last_prompt_id = str(task_id)
        execution_start_time = time.perf_counter()
        prompt_executor.execute(
            ACTIVE_TASK["flow_comfy"],
            str(task_id),
            {"client_id": "vix"},
            [str(i["comfy_node_id"]) for i in ACTIVE_TASK["outputs"]],
        )
        current_time = time.perf_counter()
        if ACTIVE_TASK["interrupt"] is False:
            ACTIVE_TASK.pop("nodes_count")
            ACTIVE_TASK.pop("current_node")
            if not ACTIVE_TASK["error"]:
                ACTIVE_TASK["progress"] = 100.0
            TASKS_HISTORY[task_id] = ACTIVE_TASK
        TASKS_QUEUE.pop(task_id, 0)
        ACTIVE_TASK = {}
        LOGGER.info("Prompt executed in %f seconds", current_time - execution_start_time)
        need_gc = True


async def start_tasks_engine(
    tasks_files_dir: str,
    ui_mode: bool,
    comfy_queue: typing.Any,
    exit_event: asyncio.Event,
) -> None:
    async def start_background_tasks_engine(prompt_executor):
        await asyncio.to_thread(background_prompt_executor, prompt_executor, exit_event)

    if ui_mode:
        load_tasks(tasks_files_dir)
        _ = asyncio.create_task(tasks_background_sync(tasks_files_dir))
    _ = asyncio.create_task(start_background_tasks_engine(comfy_queue))  # noqa


async def tasks_background_sync(tasks_files_dir: str):
    try:
        while True:
            await asyncio.sleep(3)
            save_tasks(tasks_files_dir)
    except asyncio.CancelledError:
        LOGGER.info("Cancelling..")
        n_tasks = save_tasks(tasks_files_dir)
        LOGGER.info("Cancelled, saved %s tasks.", n_tasks)
        raise
