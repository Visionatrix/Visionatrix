"""
Many parts of code in this file was taken and adjustment from the ComfyUI repository:

https://github.com/comfyanonymous/ComfyUI
"""

# pylint: skip-file

import asyncio
import contextlib
import enum
import gc
import importlib.util
import logging
import os
import subprocess
import sys
import threading
import time
import typing
import uuid
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from socket import gethostname

from psutil import virtual_memory

from . import _version, options
from .pydantic_models import ComfyUIFolderPathDefinition

LOGGER = logging.getLogger("visionatrix")

SYSTEM_DETAILS = {
    "hostname": gethostname(),
    "os": os.name,
    "version": sys.version,
    "embedded_python": options.PYTHON_EMBEDED,
}
TORCH_VERSION: str | None = None
PROMPT_EXECUTOR: typing.Any


async def load(
    task_progress_callback,
) -> [typing.Callable[[dict], tuple[bool, dict, list, list]], typing.Any, typing.Any]:

    # for diffusers/transformers library
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"

    if "NO_ALBUMENTATIONS_UPDATE" not in os.environ:
        os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"  # disable checking if new version of "Albumentations" is available

    if sys.platform.lower() == "darwin":
        # SUPIR node: 'aten::upsample_bicubic2d.out' is not currently implemented for the MPS device
        # BiRefNet: torchvision::deform_conv2d
        if "PYTORCH_ENABLE_MPS_FALLBACK" not in os.environ:
            os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    if options.PYTHON_EMBEDED and importlib.util.find_spec("torch") is None:
        # we remove pytorch from the Windows standalone release, so that the archive with the release is smaller.
        LOGGER.info("PyTorch is not installed. Installing torch, torchvision, torchaudio.")

        for attempt in range(3):
            try:
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "torch",
                        "torchvision",
                        "torchaudio",
                        "--index-url",
                        "https://download.pytorch.org/whl/cu128",
                        # !!! do not forget to change PyTorch version in "scripts/easy_install.py" !!!
                    ]
                )
                LOGGER.info("Successfully installed PyTorch packages.")
                break
            except subprocess.CalledProcessError as e:
                LOGGER.error("Attempt %d: Failed to install PyTorch packages: %s", attempt, e)
                if attempt == 2:  # 3 - 1
                    LOGGER.error("All installation attempts failed.")
                    raise e
                LOGGER.info("Retrying installation...")

    sys.path.append(options.COMFYUI_DIR)

    original_argv = sys.argv[:]
    if task_progress_callback is None and "--cpu" not in sys.argv:
        sys.argv.append("--cpu")
    elif "--disable-device-detection" not in sys.argv and "--cpu" not in sys.argv and "--directml" not in sys.argv:
        if need_directml_flag():
            sys.argv.append("--directml")
        elif need_cpu_flag():
            sys.argv.append("--cpu")

    LOGGER.debug("ComfyUI command line arguments: %s", sys.argv)
    fill_comfyui_args()
    sys.argv = original_argv

    import folder_paths  # noqa # isort: skip

    folder_paths.models_dir = options.MODELS_DIR
    for i in get_autoconfigured_model_folders_from(options.MODELS_DIR):
        add_model_folder_path(i.folder_key, i.path, True)

    os.environ["COMFYUI_MODEL_PATH"] = options.MODELS_DIR  # for ComfyUI-Impact-Pack and maybe others

    os.environ["COMFYUI_PATH"] = options.COMFYUI_DIR  # for ComfyUI-Impact-Pack and maybe others

    folder_paths.set_output_directory(str(Path(options.OUTPUT_DIR)))
    folder_paths.set_input_directory(str(Path(options.INPUT_DIR)))
    folder_paths.set_user_directory(str(Path(options.USER_DIR)))

    import main  # noqa # isort: skip
    import execution  # noqa # isort: skip
    import nodes  # noqa # isort: skip
    import server  # noqa # isort: skip

    if main.args.cuda_device is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(main.args.cuda_device)
        LOGGER.info("Set cuda device to: %s", main.args.cuda_device)

    import cuda_malloc  # noqa

    # StartComfyUI: copy of code from ComfyUIs 'main.py'
    if main.args.temp_directory:
        temp_dir = os.path.join(os.path.abspath(main.args.temp_directory), "temp")
        logging.info("Setting temp directory to: %s", temp_dir)
        folder_paths.set_temp_directory(temp_dir)
    main.cleanup_temp()

    prompt_server = get_comfy_prompt_server_class_instance(task_progress_callback)

    nodes.init_extra_nodes(init_custom_nodes=True)

    main.cuda_malloc_warning()

    prompt_server.add_routes()
    main.hijack_progress(prompt_server)

    os.makedirs(folder_paths.get_temp_directory(), exist_ok=True)

    async def start_all():
        await prompt_server.setup()
        await main.run(
            prompt_server,
            address="127.0.0.1",
            port=8188,
            verbose=False,
            call_on_start=None,
        )

    return execution.validate_prompt, [prompt_server.prompt_queue, prompt_server], start_all


def get_autoconfigured_model_folders_from(models_dir: str) -> list[ComfyUIFolderPathDefinition]:
    paths_to_preconfigure = {
        "checkpoints": "checkpoints",
        "text_encoders": "text_encoders",
        "clip_vision": "clip_vision",
        "controlnet": "controlnet",
        "diffusion_models": "diffusion_models",
        "diffusers": "diffusers",
        "ipadapter": "ipadapter",
        "instantid": "instantid",
        "loras": ["loras", "photomaker"],
        "photomaker": "photomaker",
        "sams": "sams",
        "style_models": "style_models",
        "ultralytics": "ultralytics",
        "ultralytics_bbox": "ultralytics/bbox",
        "ultralytics_segm": "ultralytics/segm",
        "unet": "unet",
        "upscale_models": "upscale_models",
        "vae": "vae",
        "vae_approx": "vae_approx",
        "pulid": "pulid",
        "birefnet": ["BiRefNet", "birefnet"],
    }

    comfyui_folders = []
    for folder_key, subpaths in paths_to_preconfigure.items():
        if isinstance(subpaths, str):
            subpaths = [subpaths]
        for subpath in reversed(subpaths):
            absolute_new_path = str(Path(models_dir).joinpath(subpath))
            if not Path(absolute_new_path).is_absolute():
                absolute_new_path = str(Path(options.COMFYUI_DIR).joinpath(absolute_new_path).resolve())
            folder_def = ComfyUIFolderPathDefinition(folder_key=folder_key, path=absolute_new_path)
            comfyui_folders.append(folder_def)
    return comfyui_folders


def get_comfy_prompt_server_class_instance(task_progress_callback):
    import execution  # noqa
    import server  # noqa

    class ComfyPromptServer(server.PromptServer):

        def send_sync(self, event, data, sid=None):  # noqa
            task_progress_callback(event, data)
            super().send_sync(event, data, sid)

        def post_prompt(self, json_data: dict):  # noqa
            json_data = self.trigger_on_prompt(json_data)

            if "number" in json_data:
                number = float(json_data["number"])
            else:
                number = self.number
                if json_data.get("front"):
                    number = -number

                self.number += 1

            if "prompt" in json_data:
                prompt = json_data["prompt"]
                valid = execution.validate_prompt(prompt)
                extra_data = {}
                if "extra_data" in json_data:
                    extra_data = json_data["extra_data"]

                if "client_id" in json_data:
                    extra_data["client_id"] = json_data["client_id"]
                if valid[0]:
                    prompt_id = json_data["prompt_id"] if "prompt_id" in json_data else str(uuid.uuid4())
                    outputs_to_execute = valid[2]
                    self.prompt_queue.put((number, prompt_id, prompt, extra_data, outputs_to_execute))
                    return {"prompt_id": prompt_id, "number": number, "node_errors": valid[3]}
                return {"error": valid[1], "node_errors": valid[3]}
            return {"error": "no prompt", "node_errors": []}

    try:
        asyncio_loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(asyncio_loop)
    return ComfyPromptServer(asyncio_loop)


def get_node_class_mappings() -> dict[str, object]:
    import nodes  # noqa

    return nodes.NODE_CLASS_MAPPINGS


def get_folder_names_and_paths() -> dict[str, tuple[list[str], set[str]]]:
    import folder_paths  # noqa

    return folder_paths.folder_names_and_paths


def add_model_folder_path(folder_name: str, full_folder_path: str, is_default: bool = False) -> None:
    import folder_paths  # noqa

    folder_paths.add_model_folder_path(folder_name, full_folder_path, is_default)


def interrupt_processing() -> None:
    import nodes  # noqa

    nodes.interrupt_processing()


def unload_all_models() -> None:
    import comfy  # noqa

    comfy.model_management.unload_all_models()


def soft_empty_cache() -> None:
    import comfy  # noqa

    comfy.model_management.soft_empty_cache()


def get_engine_details() -> dict:
    import comfy  # noqa

    return {
        "disable_smart_memory": bool(comfy.model_management.DISABLE_SMART_MEMORY),
        "vram_state": str(comfy.model_management.vram_state.name),
    }


def get_root_models_dir() -> str:
    import folder_paths  # noqa

    return folder_paths.models_dir


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
    global TORCH_VERSION

    if not TORCH_VERSION:
        import torch  # noqa

        if torch.version.cuda is not None:
            TORCH_VERSION = f"{torch.__version__} (CUDA {torch.version.cuda})"
        elif torch.version.hip is not None:
            TORCH_VERSION = f"{torch.__version__} (ROCm {torch.version.hip})"
        else:
            TORCH_VERSION = torch.__version__

    return {
        "worker_version": _version.__version__,
        "pytorch_version": TORCH_VERSION,
        "system": SYSTEM_DETAILS,
        "ram_total": virtual_memory().total,
        "ram_free": virtual_memory().available,
        "devices": [torch_device_info()],
        "engine_details": get_engine_details(),
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


def background_prompt_executor_comfy(prompt_executor_args: tuple | list, exit_event: threading.Event):
    global PROMPT_EXECUTOR

    import comfy  # noqa
    import execution  # noqa

    q = prompt_executor_args[0]
    prompt_server = prompt_executor_args[1]

    current_time: float = 0.0
    PROMPT_EXECUTOR = execution.PromptExecutor(prompt_server, cache_type=execution.CacheType.CLASSIC, cache_size=0)
    last_gc_collect = 0
    need_gc = False
    gc_collect_interval = 10.0

    while True:
        timeout = 1.0
        if need_gc:
            timeout = max(gc_collect_interval - (current_time - last_gc_collect), 0.0)

        queue_item = q.get(timeout=timeout)
        if exit_event.is_set():
            break

        if queue_item is not None:
            item, item_id = queue_item

            if item[3].get("unload_models"):
                comfy.model_management.unload_all_models()
                gc.collect()
                comfy.model_management.soft_empty_cache()
                last_gc_collect = time.perf_counter()

            execution_start_time = time.perf_counter()
            prompt_id = item[1]
            prompt_server.last_prompt_id = prompt_id

            PROMPT_EXECUTOR.execute(item[2], prompt_id, item[3], item[4])
            need_gc = True
            q.task_done(
                item_id,
                PROMPT_EXECUTOR.history_result,
                status=execution.PromptQueue.ExecutionStatus(
                    status_str="success" if PROMPT_EXECUTOR.success else "error",
                    completed=PROMPT_EXECUTOR.success,
                    messages=PROMPT_EXECUTOR.status_messages,
                ),
            )
            if prompt_server.client_id is not None:
                prompt_server.send_sync("executing", {"node": None, "prompt_id": prompt_id}, prompt_server.client_id)

            current_time = time.perf_counter()
            execution_time = current_time - execution_start_time
            logging.info("Prompt executed in %.2f seconds", execution_time)

        flags = q.get_flags()
        free_memory = flags.get("free_memory", False)

        if flags.get("unload_models", free_memory):
            comfy.model_management.unload_all_models()
            need_gc = True
            last_gc_collect = 0

        if free_memory:
            PROMPT_EXECUTOR.reset()
            need_gc = True
            last_gc_collect = 0

        if need_gc:
            current_time = time.perf_counter()
            if (current_time - last_gc_collect) > gc_collect_interval:
                gc.collect()
                comfy.model_management.soft_empty_cache()
                last_gc_collect = current_time
                need_gc = False


def add_arguments(parser):
    parser.add_argument(
        "--extra-model-paths-config",
        type=str,
        default=None,
        metavar="PATH",
        nargs="+",
        action="append",
        help="Load one or more extra_model_paths.yaml files.",
    )
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
    fpunet_group.add_argument("--fp32-unet", action="store_true", help="Run the diffusion model in fp32.")
    fpunet_group.add_argument("--fp64-unet", action="store_true", help="Run the diffusion model in fp64.")
    fpunet_group.add_argument("--bf16-unet", action="store_true", help="Run the diffusion model in bf16.")
    fpunet_group.add_argument("--fp16-unet", action="store_true", help="Run the diffusion model in fp16")
    fpunet_group.add_argument("--fp8_e4m3fn-unet", action="store_true", help="Store unet weights in fp8_e4m3fn.")
    fpunet_group.add_argument("--fp8_e5m2-unet", action="store_true", help="Store unet weights in fp8_e5m2.")

    fpvae_group = parser.add_mutually_exclusive_group()
    fpvae_group.add_argument("--fp16-vae", action="store_true", help="Run the VAE in fp16, might cause black images.")
    fpvae_group.add_argument("--fp32-vae", action="store_true", help="Run the VAE in full precision fp32.")
    fpvae_group.add_argument("--bf16-vae", action="store_true", help="Run the VAE in bf16.")

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

    parser.add_argument(
        "--oneapi-device-selector",
        type=str,
        default=None,
        metavar="SELECTOR_STRING",
        help="Sets the oneAPI device(s) this instance will use.",
    )
    parser.add_argument(
        "--disable-ipex-optimize",
        action="store_true",
        help="Disables ipex.optimize default when loading models with Intel's Extension for Pytorch.",
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
    attn_group.add_argument("--use-sage-attention", action="store_true", help="Use sage attention.")
    attn_group.add_argument("--use-flash-attention", action="store_true", help="Use FlashAttention.")

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
        help="Set the amount of vram in GB you want to reserve for use by your OS/other software. "
        "By default some amount is reserved depending on your OS.",
    )

    class PerformanceFeature(enum.Enum):  # we need it only for definition, later we use Comfy "set()"
        Fp16Accumulation = "fp16_accumulation"
        Fp8MatrixMultiplication = "fp8_matrix_mult"
        CublasOps = "cublas_ops"

    parser.add_argument(
        "--fast",
        nargs="*",
        type=PerformanceFeature,
        help="Enable some untested and potentially quality deteriorating optimizations. "
        "--fast with no arguments enables everything. "
        "You can pass a list specific optimizations if you only want to enable specific ones. "
        "Current valid optimizations: fp16_accumulation fp8_matrix_mult cublas_ops",
    )
    parser.add_argument("--mmap-torch-files", action="store_true", help="Use mmap when loading ckpt/pt files.")


def fill_comfyui_args():
    import comfy.cli_args  # noqa # isort: skip

    comfy.cli_args.args, _ = comfy.cli_args.parser.parse_known_args()

    # Original ComfyUI code:
    if comfy.cli_args.args.force_fp16:
        comfy.cli_args.args.fp16_unet = True

    # '--fast' is not provided, use an empty set
    if comfy.cli_args.args.fast is None:
        comfy.cli_args.args.fast = set()
    # '--fast' is provided with an empty list, enable all optimizations
    elif comfy.cli_args.args.fast == []:
        comfy.cli_args.args.fast = set(comfy.cli_args.PerformanceFeature)
    # '--fast' is provided with a list of performance features, use that list
    else:
        comfy.cli_args.args.fast = set(comfy.cli_args.args.fast)


def set_comfy_internal_flags(
    save_metadata: bool, smart_memory: bool, cache_type: str, cache_size: int, vae_cpu: bool
) -> None:
    import comfy  # noqa
    import execution  # noqa

    comfy.cli_args.args.disable_metadata = not save_metadata

    models_were_unloaded = False

    disable_smart_memory = not smart_memory
    if comfy.cli_args.args.disable_smart_memory != disable_smart_memory:
        comfy.model_management.unload_all_models()
        models_were_unloaded = True

        comfy.cli_args.args.disable_smart_memory = disable_smart_memory
        comfy.model_management.DISABLE_SMART_MEMORY = disable_smart_memory

    if cache_type == "lru":
        cache_type = execution.CacheType.LRU
    elif cache_type == "none":
        cache_type = execution.CacheType.DEPENDENCY_AWARE
    else:
        cache_type = execution.CacheType.CLASSIC

    if PROMPT_EXECUTOR.cache_type != cache_type or PROMPT_EXECUTOR.cache_size != cache_size:
        PROMPT_EXECUTOR.cache_type = cache_type
        PROMPT_EXECUTOR.cache_size = cache_size
        PROMPT_EXECUTOR.reset()

    if comfy.cli_args.args.cpu_vae != vae_cpu:
        if not models_were_unloaded:
            comfy.model_management.unload_all_models()
        comfy.cli_args.args.cpu_vae = vae_cpu
