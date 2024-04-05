"""
Many parts of code in this file was taken and adjustment from the ComfyUI repository:

https://github.com/comfyanonymous/ComfyUI
"""

# pylint: skip-file

import asyncio
import contextlib
import logging
import os
import re
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
    ]
    args_to_remove = []
    for i, c in enumerate(sys.argv):
        for k in filter_list:
            if re.search(k, c) is not None:
                args_to_remove.append(i)

    args_to_remove.sort(reverse=True)
    for i in args_to_remove:
        sys.argv.pop(i)

    LOGGER.debug("command line arguments: %s", sys.argv)

    if sys.platform.lower() == "darwin":
        # SUPIR node: 'aten::upsample_bicubic2d.out' is not currently implemented for the MPS device
        if "PYTORCH_ENABLE_MPS_FALLBACK" not in os.environ:
            os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    if need_directml_flag() and "--directml" not in sys.argv:
        sys.argv.append("--directml")
    elif need_cpu_flag() and "--cpu" not in sys.argv:
        sys.argv.append("--cpu")

    import main  # noqa # isort: skip
    import execution  # noqa # isort: skip
    import folder_paths  # noqa # isort: skip
    import nodes  # noqa # isort: skip
    import server  # noqa # isort: skip

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


def cleanup_models() -> None:
    import comfy  # noqa

    comfy.model_management.cleanup_models()


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

    parser.add_argument(
        "--dont-upcast-attention",
        action="store_true",
        help="Disable upcasting of attention. Can boost speed but increase the chances of black images.",
    )

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
        "--disable-smart-memory",
        action="store_true",
        help="Force ComfyUI to aggressively offload to regular ram instead of keeping models in vram when it can.",
    )
