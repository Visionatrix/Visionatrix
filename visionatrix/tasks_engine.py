import asyncio
import builtins
import contextlib
import json
import logging
import os
import subprocess
import sys
import threading
import uuid
from importlib.metadata import PackageNotFoundError, version

import httpx
from websockets import client

from . import options

LOGGER = logging.getLogger("visionatrix")
COMFY_PROCESS: subprocess.Popen[bytes] | None = None
BACKGROUND_TASKS_ENGINE: asyncio.Task | None = None
BACKGROUND_TASKS_SYNC: asyncio.Task | None = None

TASKS_HISTORY = {}
"""{
    task_id: {
        progress: 0.0-100.0,
        error: "",
        name: "",
        input_params: "",
        outputs: [int],
        started: bool,  # TO-DO: remove
        input_files: [],  # TO-DO: remove
        flow_comfy: {},  # TO-DO: remove
        interrupt: bool,  # TO-DO: remove
        prompt_id: "",  # TO-DO: remove
        }
    }"""
TASKS_QUEUE = {}
"""{
    task_id: {
        progress: 0.0-100.0,
        error: "",
        name: "",
        input_params: "",
        outputs: [int],
        started: bool,
        input_files: [],
        flow_comfy: {},
        interrupt: bool,
        prompt_id: "",  # TO-DO: remove
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
        "started": False,
        "input_files": [],
        "flow_comfy": {},
        "interrupt": False,
        "prompt_id": "",
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


async def track_task_progress(
    connection: client.WebSocketClientProtocol,
    task_id: int,
    task_details: dict,
    prompt_id: str,
    nodes_count: int,
    tasks_files_dir: str,
) -> None:
    node_percent = 100 / nodes_count
    current_node = ""
    while True:
        if task_details["interrupt"]:
            LOGGER.debug("interrupting %s with progress %s", task_id, task_details["progress"])
            await httpx.AsyncClient().post(url=f"http://{options.get_comfy_address()}/interrupt")
            remove_task(task_id, tasks_files_dir)
            return
        out = await connection.recv()
        if isinstance(out, str):
            message = json.loads(out)
            LOGGER.debug("received from ComfyUI: %s", message)
            data = message.get("data", {})
            if message["type"] == "execution_start" and data.get("prompt_id", "") == prompt_id:
                task_details["started"] = True
            elif message["type"] == "executing":
                if data["node"] is None and data["prompt_id"] == prompt_id:
                    task_details["progress"] = 100.0
                    break
                if data["node"] is not None and data["prompt_id"] == prompt_id:
                    if not current_node:
                        current_node = data["node"]
                    if current_node != data["node"]:
                        task_details["progress"] += node_percent
                        current_node = data["node"]
            elif message["type"] == "progress" and "max" in data and "value" in data:
                current_node = ""
                task_details["progress"] += node_percent / int(data["max"])
            elif message["type"] == "execution_error" and data.get("prompt_id", "") == prompt_id:
                task_details["error"] = data["exception_message"]
                LOGGER.error(
                    "Exception occurred during executing task %s:\n%s\n%s",
                    task_id,
                    data["exception_message"],
                    data["traceback"],
                )
                break
            elif message["type"] == "execution_interrupted" and data.get("prompt_id", "") == prompt_id:
                LOGGER.debug("execution interrupted: %s with progress %s", task_id, task_details["progress"])
                remove_task(task_id, tasks_files_dir)
                return
        else:
            continue
    LOGGER.debug("remove input files for %s task", task_id)
    remove_task_files(task_id, tasks_files_dir, ["input"])


def save_tasks(tasks_files_dir: str) -> int:
    tasks = TASKS_QUEUE | TASKS_HISTORY
    with builtins.open(os.path.join(tasks_files_dir, "tasks_history.json"), mode="w", encoding="UTF-8") as file:
        json.dump(tasks, file)
    LOGGER.debug("saved %s tasks", len(tasks))
    return len(tasks)


def load_tasks(tasks_files_dir: str):
    global NEXT_TASK_ID  # pylint: disable=global-statement

    tasks_history = os.path.join(tasks_files_dir, "tasks_history.json")
    if os.path.exists(tasks_history):
        with builtins.open(tasks_history, mode="r", encoding="UTF-8") as file:
            for k, v in json.load(file).items():
                if v["progress"] < 100 and not v["error"]:
                    TASKS_QUEUE.update({int(k): v})
                else:
                    TASKS_HISTORY.update({int(k): v})
        LOGGER.info("Loaded %s tasks", len(TASKS_HISTORY))
    else:
        LOGGER.info("No `tasks_history.json` to load.")
    NEXT_TASK_ID = 1 + max(TASKS_HISTORY.keys(), default=0)


async def background_tasks_engine(backend_dir: str, tasks_files_dir: str):
    global COMFY_PROCESS, BACKGROUND_TASKS_ENGINE  # pylint: disable=global-statement

    comfy_process: subprocess.Popen[bytes] | None = None
    comfy_track_connection: client.WebSocketClientProtocol | None = None
    client_id = str(uuid.uuid4())
    try:
        run_cmd = [
            sys.executable,
            os.path.join(backend_dir, "main.py"),
            "--port",
            str(options.get_comfy_port()),
            "--output-directory",
            os.path.join(tasks_files_dir, "output"),
            "--input-directory",
            os.path.join(tasks_files_dir, "input"),
        ]
        if need_directml_flag():
            run_cmd += ["--directml"]
        stdout = None if LOGGER.getEffectiveLevel == logging.DEBUG or options.COMFY_DEBUG != "0" else subprocess.DEVNULL
        stderr = None if LOGGER.getEffectiveLevel == logging.INFO or options.COMFY_DEBUG != "0" else subprocess.DEVNULL
        comfy_process = subprocess.Popen(run_cmd, stdout=stdout, stderr=stderr)  # pylint: disable=consider-using-with
        while True:
            with contextlib.suppress(Exception):
                comfy_track_connection = await client.connect(
                    f"ws://{options.get_comfy_address()}/ws?clientId={client_id}"
                )
            if comfy_track_connection is not None:
                LOGGER.info("Ready to process tasks.")
                break
        COMFY_PROCESS = comfy_process
        while True:
            if not TASKS_QUEUE:
                await asyncio.sleep(0.01)
                continue

            task_id, task_details = next(iter(TASKS_QUEUE.items()))
            r = await httpx.AsyncClient().post(
                f"http://{options.get_comfy_address()}/prompt",
                json={"prompt": task_details["flow_comfy"], "client_id": client_id},
            )
            if r.status_code != 200:
                task_details["error"] = f"ComfyUI does not accepted flow, status={r.status_code}"
                LOGGER.error(task_details["error"])
                TASKS_HISTORY[task_id] = task_details
                TASKS_QUEUE.pop(task_id, None)
                continue
            task_details["started"] = True
            await track_task_progress(
                comfy_track_connection,
                task_id,
                task_details,
                json.loads(r.text)["prompt_id"],
                len(list(task_details["flow_comfy"].keys())),
                tasks_files_dir,
            )
            TASKS_HISTORY[task_id] = task_details
            TASKS_QUEUE.pop(task_id, None)
    except asyncio.CancelledError:
        LOGGER.info("Cancelling..")
        if comfy_track_connection is not None:
            with contextlib.suppress(Exception):
                await comfy_track_connection.close()
        if comfy_process is not None:
            with contextlib.suppress(BaseException):
                comfy_process.kill()
            COMFY_PROCESS = None
        if BACKGROUND_TASKS_SYNC is not None:
            BACKGROUND_TASKS_SYNC.cancel()
        LOGGER.info("Cancelled.")
        BACKGROUND_TASKS_ENGINE = None
        raise


async def start_tasks_engine(backend_dir: str, tasks_files_dir: str, ui_mode: bool) -> None:
    global BACKGROUND_TASKS_ENGINE, BACKGROUND_TASKS_SYNC  # pylint: disable=global-statement

    BACKGROUND_TASKS_SYNC = None
    tasks_engine = asyncio.create_task(background_tasks_engine(backend_dir, tasks_files_dir))
    for _ in range(15 * 2):
        if COMFY_PROCESS is not None:
            if ui_mode:
                load_tasks(tasks_files_dir)
                BACKGROUND_TASKS_SYNC = asyncio.create_task(tasks_background_sync(tasks_files_dir))
            BACKGROUND_TASKS_ENGINE = tasks_engine
            return
        await asyncio.sleep(0.5)
    tasks_engine.cancel()
    raise RuntimeError("Error connecting to ComfyUI")


async def stop_tasks_engine() -> None:
    if BACKGROUND_TASKS_ENGINE is not None:
        BACKGROUND_TASKS_ENGINE.cancel()
    for _ in range(15 * 10):
        if BACKGROUND_TASKS_ENGINE is None:
            return
        await asyncio.sleep(0.1)


def need_directml_flag() -> bool:
    if sys.platform.lower() != "win32":
        return False

    try:
        version("torch-directml")
        LOGGER.info("DirectML package is present.")
        return True
    except PackageNotFoundError:
        LOGGER.info("No DirectML package found.")
        return False


async def tasks_background_sync(tasks_files_dir: str):
    global BACKGROUND_TASKS_SYNC  # pylint: disable=global-statement

    try:
        while True:
            await asyncio.sleep(3)
            save_tasks(tasks_files_dir)
    except asyncio.CancelledError:
        LOGGER.info("Cancelling..")
        n_tasks = save_tasks(tasks_files_dir)
        LOGGER.info("Cancelled, saved %s tasks.", n_tasks)
        BACKGROUND_TASKS_SYNC = None
        raise
