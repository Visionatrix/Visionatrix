import builtins
import os
from shutil import rmtree
from subprocess import run

from .. import options
from .custom_nodes import install_base_custom_nodes

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


def install(backend_dir="", flows_dir="", models_dir="") -> None:
    """Performs clean installation."""
    flows_dir = options.get_flows_dir(flows_dir)
    if os.path.exists(flows_dir) is True:
        print("Removing existing Flows directory")
        rmtree(flows_dir)
    os.makedirs(flows_dir)
    models_dir = options.get_models_dir(models_dir)
    if os.path.exists(models_dir) is True:
        print("Removing existing Models directory")
        rmtree(models_dir)
    os.makedirs(models_dir)
    backend_dir = options.get_backend_dir(backend_dir)
    if os.path.exists(backend_dir) is True:
        print("Removing existing Backend directory")
        rmtree(backend_dir)
    os.makedirs(backend_dir)
    run(f"git clone https://github.com/cloud-media-flows/ComfyUI.git {backend_dir}".split(), check=True)
    run(f"python -m pip install -r {os.path.join(backend_dir, 'requirements.txt')}".split(), check=True)
    with builtins.open(os.path.join(backend_dir, "extra_model_paths.yaml"), "w", encoding="utf-8") as fp:
        fp.write(EXTRA_MODEL_PATHS.replace("amw_models_root", models_dir))
    install_base_custom_nodes(os.path.join(backend_dir, "custom_nodes"))
