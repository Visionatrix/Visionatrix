import builtins
import logging
import os
import stat
import sys
from pathlib import Path
from shutil import rmtree
from subprocess import check_call, run

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
  diffusion_models: |
    vix_models_root/diffusion_models
    vix_models_root/unet
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
  pulid: vix_models_root/pulid
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
        check_call(["git", "clone", "https://github.com/Visionatrix/ComfyUI.git", options.BACKEND_DIR])
        if not Version(_version.__version__).is_devrelease:
            clone_env = os.environ.copy()
            clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
            check_call(["git", "checkout", f"tags/v{_version.__version__}"], env=clone_env, cwd=options.BACKEND_DIR)
        run(
            [sys.executable, "-m", "pip", "install", "-r", os.path.join(options.BACKEND_DIR, "requirements.txt")],
            check=True,
        )
        os.makedirs(os.path.join(options.BACKEND_DIR, "user"), exist_ok=True)  # for multiprocessing installations
        create_missing_models_dirs()
        with builtins.open(os.path.join(options.BACKEND_DIR, "extra_model_paths.yaml"), "w", encoding="utf-8") as fp:
            fp.write(EXTRA_MODEL_PATHS.replace("vix_models_root", options.MODELS_DIR))
        install_base_custom_nodes()


def create_missing_models_dirs() -> None:
    for k in yaml.safe_load(EXTRA_MODEL_PATHS)["vix_models"]:
        if (v := Path(options.BACKEND_DIR).joinpath("models", k)).exists() is False:
            os.makedirs(v, exist_ok=True)
