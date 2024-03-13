import json
import os

from websockets.sync.client import ClientConnection

TASKS_STORAGE = {}
"""{task_id: {progress: 0.0-100.0, error: "", name: "", input_params: "", input_files: [str], outputs: [int]}}"""


def get_new_task_id() -> int:
    if not TASKS_STORAGE:
        return 1
    keys = TASKS_STORAGE.keys()
    max_key = max(keys)
    for i in range(1, max_key + 2):
        if i not in keys:
            return i
    return 999999999999


def create_new_task(input_params: dict, backend_dir: str) -> [int, dict]:
    task_details = {
        "input_params": input_params,
        "progress": 0.0,
        "error": "",
        "input_files": [],
        "outputs": [],
    }
    task_id = get_new_task_id()
    remove_task_files(task_id, backend_dir, ["output", "input"])
    TASKS_STORAGE[task_id] = task_details
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
                os.remove(os.path.join(target_directory, filename))


def track_task_progress(
    connection: ClientConnection, prompt_id: str, task_id: int, task_details: dict, nodes_count: int, backend_dir: str
) -> None:
    node_percent = 100 / nodes_count
    current_node = ""
    while True:
        out = connection.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message["type"] == "executing":
                data = message["data"]
                if data["node"] is None and data["prompt_id"] == prompt_id:
                    task_details["progress"] = 100
                    remove_task_files(task_id, backend_dir, ["inputs"])
                    break
                if data["node"] is not None and data["prompt_id"] == prompt_id:
                    if not current_node:
                        current_node = data["node"]
                    if current_node != data["node"]:
                        task_details["progress"] += node_percent
                        current_node = data["node"]
            elif message["type"] == "progress":
                data = message["data"]
                if "max" in data and "value" in data:
                    current_node = ""
                    task_details["progress"] += node_percent / int(data["max"])
        else:
            continue
