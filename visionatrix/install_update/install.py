import builtins
import logging
import os
import stat
import sys
from pathlib import Path
from shutil import rmtree
from subprocess import run

import yaml
from packaging.version import Version

from .. import _version, options
from .custom_nodes import install_base_custom_nodes

LOGGER = logging.getLogger("visionatrix")
EXTRA_MODEL_PATHS = """
vix_models:
  checkpoints: vix_models_root/checkpoints
  clip: vix_models_root/clip
  clip_vision: vix_models_root/clip_vision
  controlnet: vix_models_root/controlnet
  diffusers: vix_models_root/diffusers
  ipadapter: vix_models_root/ipadapter
  instantid: vix_models_root/instantid
  loras: |
    vix_models_root/loras
    vix_models_root/photomaker
  photomaker: vix_models_root/photomaker
  sams: vix_models_root/sams
  ultralytics: vix_models_root/ultralytics
  unet: vix_models_root/unet
  upscale_models: vix_models_root/upscale_models
  vae: vix_models_root/vae
  vae_approx: vix_models_root/vae_approx
"""


def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def install(operations_mask: list[bool]) -> None:
    """Performs a clean installation on the provided directories."""
    if operations_mask[1]:
        if os.path.exists(options.FLOWS_DIR) is True:
            LOGGER.info("Removing existing Flows directory: %s", options.FLOWS_DIR)
            rmtree(options.FLOWS_DIR, onerror=remove_readonly)
        os.makedirs(options.FLOWS_DIR)
    if operations_mask[2]:
        if os.path.exists(options.MODELS_DIR) is True:
            LOGGER.info("Removing existing Models directory: %s", options.MODELS_DIR)
            rmtree(options.MODELS_DIR, onerror=remove_readonly)
        os.makedirs(options.MODELS_DIR)
    if operations_mask[0]:
        if os.path.exists(options.BACKEND_DIR) is True:
            LOGGER.info("Removing existing Backend directory: %s", options.BACKEND_DIR)
            rmtree(options.BACKEND_DIR, onerror=remove_readonly)
        os.makedirs(options.BACKEND_DIR)
        clone_command = "git clone "
        what_where_clone = f"https://github.com/Visionatrix/ComfyUI.git {options.BACKEND_DIR}"
        clone_env = None
        if options.PYTHON_EMBEDED:
            clone_command += "--depth 1 " + what_where_clone
        elif Version(_version.__version__).is_devrelease:
            clone_command += what_where_clone
        else:
            clone_env = os.environ.copy()
            clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
            clone_command += f"-b v{_version.__version__} " + what_where_clone
        print("Executing: ", clone_command)
        run(clone_command.split(), check=True, env=clone_env)
        run(
            [sys.executable, "-m", "pip", "install", "-r", os.path.join(options.BACKEND_DIR, "requirements.txt")],
            check=True,
        )
        create_missing_models_dirs()
        with builtins.open(os.path.join(options.BACKEND_DIR, "extra_model_paths.yaml"), "w", encoding="utf-8") as fp:
            fp.write(EXTRA_MODEL_PATHS.replace("vix_models_root", options.MODELS_DIR))
        install_base_custom_nodes()


def create_missing_models_dirs() -> None:
    for k in yaml.safe_load(EXTRA_MODEL_PATHS)["vix_models"]:
        if (v := Path(options.BACKEND_DIR).joinpath("models", k)).exists() is False:
            os.makedirs(v, exist_ok=True)
