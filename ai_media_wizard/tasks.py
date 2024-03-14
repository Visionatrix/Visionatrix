import builtins
import contextlib
import json
import logging
import os
import threading

import httpx
from websockets.sync.client import ClientConnection

from . import options

LOGGER = logging.getLogger("ai_media_wizard")
TASKS_STORAGE = {}
"""{
    task_id: {
        progress: 0.0-100.0,
        error: "",
        name: "",
        input_params: "",
        input_files: [str],
        outputs: [int],
        started: bool,
        interrupt: bool,
        prompt_id: ""
        }
    }"""
TASKS_STORAGE_LOCK = threading.RLock()


def get_new_task_id() -> int:
    if not TASKS_STORAGE:
        return 1
    keys = TASKS_STORAGE.keys()
    max_key = max(keys)
    for i in range(1, max_key + 2):
        if i not in keys:
            return i
    return 999999999999


def create_new_task(name: str, input_params: dict, tasks_files_dir: str) -> [int, dict]:
    task_details = {
        "input_params": input_params,
        "progress": 0.0,
        "error": "",
        "name": name,
        "input_files": [],
        "outputs": [],
        "started": False,
        "interrupt": False,
        "prompt_id": "",
    }
    TASKS_STORAGE_LOCK.acquire()  # pylint: disable=consider-using-with
    task_id = get_new_task_id()
    TASKS_STORAGE[task_id] = task_details
    TASKS_STORAGE_LOCK.release()
    remove_task_files(task_id, tasks_files_dir, ["output", "input"])
    return task_id, task_details


def get_task(task_id: int) -> dict:
    return TASKS_STORAGE.get(task_id)


def get_tasks() -> dict:
    return TASKS_STORAGE


def update_task(task_id: int, task_details: dict) -> None:
    TASKS_STORAGE[task_id] = task_details


def remove_task(task_id: int, backend_dir: str) -> None:
    TASKS_STORAGE.pop(task_id, None)
    remove_task_files(task_id, backend_dir, ["output", "input"])


def remove_task_files(task_id: int, backend_dir: str, directories: list[str]) -> None:
    if not backend_dir:
        return
    for directory in directories:
        result_prefix = f"{task_id}_"
        target_directory = os.path.join(backend_dir, directory)
        for filename in os.listdir(target_directory):
            if filename.startswith(result_prefix):
                with contextlib.suppress(FileNotFoundError):
                    os.remove(os.path.join(target_directory, filename))


def track_task_progress(
    connection: ClientConnection, task_id: int, task_details: dict, nodes_count: int, tasks_files_dir: str
) -> None:
    node_percent = 100 / nodes_count
    current_node = ""
    while True:
        try:
            out = connection.recv(timeout=1.0)
        except TimeoutError:
            out = None
        if task_id not in TASKS_STORAGE or task_details["interrupt"]:
            break
        if isinstance(out, str):
            message = json.loads(out)
            LOGGER.debug("received from ComfyUI: %s", message)
            data = message.get("data", {})
            if message["type"] == "execution_start" and data.get("prompt_id", "") == task_details["prompt_id"]:
                task_details["started"] = True
            elif message["type"] == "executing":
                if data["node"] is None and data["prompt_id"] == task_details["prompt_id"]:
                    task_details["progress"] = 100.0
                    break
                if data["node"] is not None and data["prompt_id"] == task_details["prompt_id"]:
                    if not current_node:
                        current_node = data["node"]
                    if current_node != data["node"]:
                        task_details["progress"] += node_percent
                        current_node = data["node"]
            elif message["type"] == "progress" and "max" in data and "value" in data:
                current_node = ""
                task_details["progress"] += node_percent / int(data["max"])
            elif message["type"] == "execution_error" and data["prompt_id"] == task_details["prompt_id"]:
                task_details["error"] = data["exception_message"]
                LOGGER.error(
                    "Exception occurred during executing task %s:\n%s\n%s",
                    task_id,
                    data["exception_message"],
                    data["traceback"],
                )
                break
        else:
            continue
    if task_details["started"] and task_details["progress"] != 100.0 and not task_details["error"]:
        LOGGER.debug("interrupting %s with progress %s", task_id, task_details["progress"])
        httpx.post(url=f"http://{options.get_comfy_address()}/interrupt")
        remove_task(task_id, tasks_files_dir)
        return
    LOGGER.debug("remove input files for %s task", task_id)
    remove_task_files(task_id, tasks_files_dir, ["input"])


def save_tasks(tasks_files_dir: str):
    with builtins.open(os.path.join(tasks_files_dir, "tasks_history.json"), mode="w", encoding="UTF-8") as file:
        json.dump(TASKS_STORAGE, file)
    LOGGER.info("Saved %s tasks.", len(TASKS_STORAGE))


def load_tasks(tasks_files_dir: str):
    tasks_history = os.path.join(tasks_files_dir, "tasks_history.json")
    if os.path.exists(tasks_history):
        with builtins.open(tasks_history, mode="r", encoding="UTF-8") as file:
            for k, v in json.load(file).items():
                TASKS_STORAGE.update({int(k): v})
        LOGGER.info("Loaded %s tasks", len(TASKS_STORAGE))
    else:
        LOGGER.info("No `tasks_history.json` to load.")
