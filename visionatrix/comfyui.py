"""
Many parts of code in this file was taken and adjustment from the ComfyUI repository:

https://github.com/comfyanonymous/ComfyUI
"""

# pylint: skip-file

import contextlib
import inspect
import logging
import os
import re
import sys
import typing
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from socket import gethostname

import torch
from psutil import virtual_memory

from . import _version, options

LOGGER = logging.getLogger("visionatrix")

SYSTEM_DETAILS = {
    "hostname": gethostname(),
    "os": os.name,
    "version": sys.version,
    "embedded_python": options.PYTHON_EMBEDED,
}

if torch.version.cuda is not None:
    TORCH_VERSION = f"{torch.__version__} (CUDA {torch.version.cuda})"
elif torch.version.hip is not None:
    TORCH_VERSION = f"{torch.__version__} (ROCm {torch.version.hip})"
else:
    TORCH_VERSION = torch.__version__


def load(task_progress_callback) -> [typing.Callable[[dict], tuple[bool, dict, list, list]], typing.Any]:

    sys.path.append(options.BACKEND_DIR)

    no_device_detection = "--disable-device-detection" in sys.argv
    filter_list = [
        "--host",
        "--port",
        "--backend_dir",
        "--flows_dir",
        "--models_dir",
        "--tasks_files_dir",
        "--ui",
        "--loglevel",
        "^run$",
        "^update$",
        "^install-flow$",
        "^orphan-models$",
        "--dry-run",
        "--no-confirm",
        "--include-useful-models",
        "--file=",
        "--name=",
        "--tag=",
        "--mode",
        "--server",
        "--disable-device-detection",
        "visionatrix:APP",
    ]
    args_to_remove = []
    for i, c in enumerate(sys.argv):
        for k in filter_list:
            if re.search(k, c) is not None:
                args_to_remove.append(i)

    args_to_remove.sort(reverse=True)
    for i in args_to_remove:
        sys.argv.pop(i)

    if sys.platform.lower() == "darwin":
        # SUPIR node: 'aten::upsample_bicubic2d.out' is not currently implemented for the MPS device
        if "PYTORCH_ENABLE_MPS_FALLBACK" not in os.environ:
            os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    if task_progress_callback is None and "--cpu" not in sys.argv:
        sys.argv.append("--cpu")
    elif not no_device_detection and "--cpu" not in sys.argv and "--directml" not in sys.argv:
        if need_directml_flag():
            sys.argv.append("--directml")
        elif need_cpu_flag():
            sys.argv.append("--cpu")

    LOGGER.debug("command line arguments: %s", sys.argv)

    original_add_handler = logging.Logger.addHandler

    def out_add_handler(self, hdlr):
        stack = inspect.stack()  # Get the current stack frames
        if any(frame.function == "setup_logger" for frame in stack):
            return  # Skip adding handler (prevent duplicate logs)
        original_add_handler(self, hdlr)  # Call the original addHandler method

    logging.Logger.addHandler = out_add_handler

    import main  # noqa # isort: skip

    logging.Logger.addHandler = original_add_handler

    import execution  # noqa # isort: skip
    import folder_paths  # noqa # isort: skip
    import nodes  # noqa # isort: skip
    import server  # noqa # isort: skip

    if main.args.cuda_device is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(main.args.cuda_device)
        LOGGER.info("Set cuda device to: %s", main.args.cuda_device)

    import cuda_malloc  # noqa

    try:
        main.load_extra_path_config(Path(options.BACKEND_DIR).joinpath("extra_model_paths.yaml"))
    except AttributeError:  # September 17: remove this in ~3 months
        import utils.extra_config

        utils.extra_config.load_extra_path_config(Path(options.BACKEND_DIR).joinpath("extra_model_paths.yaml"))

    comfy_server = get_comfy_server_class(task_progress_callback)

    nodes.init_builtin_extra_nodes()
    nodes.init_external_custom_nodes()
    main.cuda_malloc_warning()

    main.hijack_progress(comfy_server)

    folder_paths.set_output_directory(str(Path(options.TASKS_FILES_DIR).joinpath("output")))
    folder_paths.add_model_folder_path("checkpoints", os.path.join(folder_paths.get_output_directory(), "checkpoints"))
    folder_paths.add_model_folder_path("clip", os.path.join(folder_paths.get_output_directory(), "clip"))
    folder_paths.add_model_folder_path("vae", os.path.join(folder_paths.get_output_directory(), "vae"))
    folder_paths.add_model_folder_path(
        "diffusion_models", os.path.join(folder_paths.get_output_directory(), "diffusion_models")
    )
    folder_paths.add_model_folder_path("loras", os.path.join(folder_paths.get_output_directory(), "loras"))
    folder_paths.set_input_directory(str(Path(options.TASKS_FILES_DIR).joinpath("input")))

    main.cleanup_temp()
    prompt_executor = get_comfy_prompt_executor(comfy_server, task_progress_callback, main.args.cache_lru)
    return execution.validate_prompt, prompt_executor


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


def get_comfy_prompt_executor(comfy_server, task_progress_callback, nodes_cache_args):
    import execution  # noqa

    class ComfyPromptExecutor(execution.PromptExecutor):

        def add_message(self, event, data, broadcast: bool):  # noqa
            task_progress_callback(event, data, broadcast)

    return ComfyPromptExecutor(comfy_server, lru_size=nodes_cache_args)


def get_node_class_mappings() -> dict[str, object]:
    import nodes  # noqa

    return nodes.NODE_CLASS_MAPPINGS


def interrupt_processing() -> None:
    import nodes  # noqa

    nodes.interrupt_processing()


def cleanup_models() -> None:
    import comfy  # noqa

    comfy.model_management.cleanup_models()


def soft_empty_cache(force: bool = False) -> None:
    import comfy  # noqa

    comfy.model_management.soft_empty_cache(force)


def torch_device_info() -> dict:
    """1:1 copy of code from ComfyUI server.py file."""
    import comfy  # noqa

    device = comfy.model_management.get_torch_device()
    device_name = comfy.model_management.get_torch_device_name(device)
    vram_total, torch_vram_total = comfy.model_management.get_total_memory(device, torch_total_too=True)
    vram_free, torch_vram_free = comfy.model_management.get_free_memory(device, torch_free_too=True)
    return {
        "name": device_name,
        "type": device.type,
        "index": 0 if device.index is None else device.index,
        "vram_total": vram_total,
        "vram_free": vram_free,
        "torch_vram_total": torch_vram_total,
        "torch_vram_free": torch_vram_free,
    }


def get_worker_details() -> dict:
    return {
        "worker_version": _version.__version__,
        "pytorch_version": TORCH_VERSION,
        "system": SYSTEM_DETAILS,
        "ram_total": virtual_memory().total,
        "ram_free": virtual_memory().available,
        "devices": [torch_device_info()],
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


def need_cpu_flag() -> bool:
    if sys.platform.lower() == "darwin":
        return False
    with contextlib.suppress(PackageNotFoundError):
        if version("torch").lower().find("rocm") != -1:
            return False

    for i in ("nvidia-cublas", "nvidia-cuda-runtime", "nvidia-cudnn", "nvidia-nccl"):
        for v in ("-cu11", "-cu12"):
            with contextlib.suppress(PackageNotFoundError):
                version(i + v)
                return False
    LOGGER.info("No CUDA or ROCM found, adding `--cpu` flag.")
    return True


def add_arguments(parser):
    parser.add_argument(
        "--cuda-device",
        type=int,
        default=None,
        metavar="DEVICE_ID",
        help="Set the id of the cuda device this instance will use.",
    )
    cm_group = parser.add_mutually_exclusive_group()
    cm_group.add_argument(
        "--cuda-malloc", action="store_true", help="Enable cudaMallocAsync (enabled by default for torch 2.0 and up)."
    )
    cm_group.add_argument("--disable-cuda-malloc", action="store_true", help="Disable cudaMallocAsync.")

    fp_group = parser.add_mutually_exclusive_group()
    fp_group.add_argument(
        "--force-fp32", action="store_true", help="Force fp32 (If this makes your GPU work better please report it)."
    )
    fp_group.add_argument("--force-fp16", action="store_true", help="Force fp16.")

    fpunet_group = parser.add_mutually_exclusive_group()
    fpunet_group.add_argument(
        "--bf16-unet", action="store_true", help="Run the UNET in bf16. This should only be used for testing stuff."
    )
    fpunet_group.add_argument("--fp16-unet", action="store_true", help="Store unet weights in fp16.")
    fpunet_group.add_argument("--fp8_e4m3fn-unet", action="store_true", help="Store unet weights in fp8_e4m3fn.")
    fpunet_group.add_argument("--fp8_e5m2-unet", action="store_true", help="Store unet weights in fp8_e5m2.")

    fpvae_group = parser.add_mutually_exclusive_group()
    fpvae_group.add_argument("--fp16-vae", action="store_true", help="Run the VAE in fp16, might cause black images.")
    fpvae_group.add_argument("--fp32-vae", action="store_true", help="Run the VAE in full precision fp32.")
    fpvae_group.add_argument("--bf16-vae", action="store_true", help="Run the VAE in bf16.")

    parser.add_argument("--cpu-vae", action="store_true", help="Run the VAE on the CPU.")

    fpte_group = parser.add_mutually_exclusive_group()
    fpte_group.add_argument(
        "--fp8_e4m3fn-text-enc", action="store_true", help="Store text encoder weights in fp8 (e4m3fn variant)."
    )
    fpte_group.add_argument(
        "--fp8_e5m2-text-enc", action="store_true", help="Store text encoder weights in fp8 (e5m2 variant)."
    )
    fpte_group.add_argument("--fp16-text-enc", action="store_true", help="Store text encoder weights in fp16.")
    fpte_group.add_argument("--fp32-text-enc", action="store_true", help="Store text encoder weights in fp32.")

    parser.add_argument(
        "--force-channels-last", action="store_true", help="Force channels last format when inferencing the models."
    )

    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument("--cache-classic", action="store_true", help="Use the old style (aggressive) caching.")
    cache_group.add_argument(
        "--cache-lru",
        type=int,
        default=0,
        help="Use LRU caching with a maximum of N node results cached. May use more RAM/VRAM.",
    )

    parser.add_argument(
        "--disable-ipex-optimize",
        action="store_true",
        help="Disables ipex.optimize when loading models with Intel GPUs.",
    )

    attn_group = parser.add_mutually_exclusive_group()
    attn_group.add_argument(
        "--use-split-cross-attention",
        action="store_true",
        help="Use the split cross attention optimization. Ignored when xformers is used.",
    )
    attn_group.add_argument(
        "--use-quad-cross-attention",
        action="store_true",
        help="Use the sub-quadratic cross attention optimization . Ignored when xformers is used.",
    )
    attn_group.add_argument(
        "--use-pytorch-cross-attention", action="store_true", help="Use the new pytorch 2.0 cross attention function."
    )

    parser.add_argument("--disable-xformers", action="store_true", help="Disable xformers.")

    upcast = parser.add_mutually_exclusive_group()
    upcast.add_argument(
        "--force-upcast-attention",
        action="store_true",
        help="Force enable attention upcasting, please report if it fixes black images.",
    )
    upcast.add_argument(
        "--dont-upcast-attention",
        action="store_true",
        help="Disable all upcasting of attention. Should be unnecessary except for debugging.",
    )

    vram_group = parser.add_mutually_exclusive_group()
    vram_group.add_argument(
        "--gpu-only",
        action="store_true",
        help="Store and run everything (text encoders/CLIP models, etc... on the GPU).",
    )
    vram_group.add_argument(
        "--highvram",
        action="store_true",
        help="By default models will be unloaded to CPU memory after being used. This option keeps them in GPU memory.",
    )
    vram_group.add_argument(
        "--normalvram", action="store_true", help="Used to force normal vram use if lowvram gets automatically enabled."
    )
    vram_group.add_argument("--lowvram", action="store_true", help="Split the unet in parts to use less vram.")
    vram_group.add_argument("--novram", action="store_true", help="When lowvram isn't enough.")
    vram_group.add_argument("--cpu", action="store_true", help="To use the CPU for everything (slow).")

    parser.add_argument(
        "--reserve-vram",
        type=float,
        default=None,
        help="Set the amount of VRAM in GB you want to reserve for use by your OS/other software.",
    )

    parser.add_argument(
        "--disable-smart-memory",
        action="store_true",
        help="Force ComfyUI to aggressively offload to regular ram instead of keeping models in vram when it can.",
    )
    parser.add_argument(
        "--fast", action="store_true", help="Enable some untested and potentially quality deteriorating optimizations."
    )
