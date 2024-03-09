import builtins
import logging
import os
import stat
from shutil import rmtree
from subprocess import run

from .custom_nodes import install_base_custom_nodes

LOGGER = logging.getLogger("ai_media_wizard")
EXTRA_MODEL_PATHS = """
amw_models:
  checkpoints: amw_models_root/checkpoints
  clip: amw_models_root/clip
  clip_vision: amw_models_root/clip_vision
  controlnet: amw_models_root/controlnet
  diffusers: amw_models_root/diffusers
  ipadapter: amw_models_root/ipadapter
  loras: |
    amw_models_root/loras
    amw_models_root/photomaker
  photomaker: amw_models_root/photomaker
  sams: amw_models_root/sams
  ultralytics: amw_models_root/ultralytics
  unet: amw_models_root/unet
  upscale_models: amw_models_root/upscale_models
  vae: amw_models_root/vae
  vae_approx: amw_models_root/vae_approx
"""


def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def install(backend_dir: str, flows_dir: str, models_dir: str) -> None:
    """Performs a clean installation on the provided directories."""
    if flows_dir:
        if os.path.exists(flows_dir) is True:
            LOGGER.info("Removing existing Flows directory: %s", flows_dir)
            rmtree(flows_dir, onerror=remove_readonly)
        os.makedirs(flows_dir)
    if models_dir:
        if os.path.exists(models_dir) is True:
            LOGGER.info("Removing existing Models directory: %s", models_dir)
            rmtree(models_dir, onerror=remove_readonly)
        os.makedirs(models_dir)
    if backend_dir:
        if os.path.exists(backend_dir) is True:
            LOGGER.info("Removing existing Backend directory: %s", backend_dir)
            rmtree(backend_dir, onerror=remove_readonly)
        os.makedirs(backend_dir)
        run(f"git clone https://github.com/cloud-media-flows/ComfyUI.git {backend_dir}".split(), check=True)
        run(f"python -m pip install -r {os.path.join(backend_dir, 'requirements.txt')}".split(), check=True)
        with builtins.open(os.path.join(backend_dir, "extra_model_paths.yaml"), "w", encoding="utf-8") as fp:
            fp.write(EXTRA_MODEL_PATHS.replace("amw_models_root", models_dir))
        install_base_custom_nodes(os.path.join(backend_dir, "custom_nodes"))
