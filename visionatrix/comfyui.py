"""
Many parts of code in this file was taken and adjustment from the ComfyUI repository:

https://github.com/comfyanonymous/ComfyUI
"""

# pylint: skip-file

import asyncio
import logging
import os
import sys
import typing
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

LOGGER = logging.getLogger("visionatrix")


def load(
    backend_dir: Path | str,
    tasks_files_dir: Path | str,
    task_progress_callback,
    exit_event: asyncio.Event,
) -> [typing.Callable[[dict], tuple[bool, dict, list, list]], typing.Any]:

    sys.path.append(backend_dir)
    sys.argv = sys.argv[:1]

    # TO-DO: options + arguments for ComfyUI
    if need_directml_flag():
        sys.argv.append("--directml")

    import execution  # noqa
    import folder_paths  # noqa
    import main  # noqa
    import nodes  # noqa
    import server  # noqa

    if main.args.cuda_device is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(main.args.cuda_device)
        LOGGER.info("Set cuda device to: %s", main.args.cuda_device)

    import cuda_malloc  # noqa

    main.cleanup_temp()
    main.load_extra_path_config(Path(backend_dir).joinpath("extra_model_paths.yaml"))

    comfy_server = get_comfy_server_class(task_progress_callback)

    nodes.init_custom_nodes()
    main.cuda_malloc_warning()

    main.hijack_progress(comfy_server)

    folder_paths.set_output_directory(str(Path(tasks_files_dir).joinpath("output")))
    folder_paths.add_model_folder_path("checkpoints", os.path.join(folder_paths.get_output_directory(), "checkpoints"))
    folder_paths.add_model_folder_path("clip", os.path.join(folder_paths.get_output_directory(), "clip"))
    folder_paths.add_model_folder_path("vae", os.path.join(folder_paths.get_output_directory(), "vae"))
    folder_paths.set_input_directory(str(Path(tasks_files_dir).joinpath("input")))

    return execution.validate_prompt, get_comfy_prompt_executor(comfy_server, task_progress_callback, exit_event)


def get_comfy_server_class(task_progress_callback):
    import server  # noqa

    class ComfyServer(server.PromptServer):

        async def send(self, event, data, sid=None):  # noqa
            LOGGER.warning("If you see this, please report, event =  %s", event)

        async def send_bytes(self, event, data, sid=None):  # noqa
            LOGGER.warning("If you see this, please report, event =  %s", event)

        def send_sync(self, event, data, sid=None):  # noqa
            task_progress_callback(event, data)

    return ComfyServer(None)


def get_comfy_prompt_executor(comfy_server, task_progress_callback, exit_event: asyncio.Event):
    import execution  # noqa

    class ComfyPromptExecutor(execution.PromptExecutor):

        def add_message(self, event, data, broadcast: bool):  # noqa
            task_progress_callback(event, data, broadcast)

    return ComfyPromptExecutor(comfy_server)


def interrupt_processing() -> None:
    import nodes  # noqa

    nodes.interrupt_processing()


def soft_empty_cache() -> None:
    import comfy  # noqa

    comfy.model_management.soft_empty_cache()


def system_stats() -> dict:
    """Full 1:1 copy of code from ComfyUI server.py file."""
    import comfy  # noqa

    device = comfy.model_management.get_torch_device()
    device_name = comfy.model_management.get_torch_device_name(device)
    vram_total, torch_vram_total = comfy.model_management.get_total_memory(device, torch_total_too=True)
    vram_free, torch_vram_free = comfy.model_management.get_free_memory(device, torch_free_too=True)
    return {
        "system": {
            "os": os.name,
            "python_version": sys.version,
            "embedded_python": os.path.split(os.path.split(sys.executable)[0])[1] == "python_embeded",
        },
        "devices": [
            {
                "name": device_name,
                "type": device.type,
                "index": device.index,
                "vram_total": vram_total,
                "vram_free": vram_free,
                "torch_vram_total": torch_vram_total,
                "torch_vram_free": torch_vram_free,
            }
        ],
    }


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
