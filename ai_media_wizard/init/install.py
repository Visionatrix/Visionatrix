import builtins
import os
from shutil import rmtree
from subprocess import run
from pathlib import Path
from .. import options

from .custom_nodes import init_base_custom_nodes
from .flows import init_basic_flows
from ..flows import get_installed_flows
import httpx


EXTRA_MODEL_PATHS = """
amw_models:
  checkpoints: amw_models_root/checkpoints
  clip: amw_models_root/clip
  clip_vision: amw_models_root/clip_vision
  controlnet: amw_models_root/controlnet
  diffusers: amw_models_root/diffusers
  ipadapter: amw_models_root/ipadapter
  loras: amw_models_root/loras
  photomaker: amw_models_root/photomaker
  sams: amw_models_root/sams
  ultratics: amw_models_root/ultratics
  unet: amw_models_root/unet
  upscale_models: amw_models_root/upscale_models
  vae: amw_models_root/vae
  vae_approx: amw_models_root/vae_approx
"""


def install(backend_dir="", flows_dir="", models_dir="") -> None:
    """Performs clean installation."""
    # Basic Flows
    flows_dir = options.get_flows_dir(flows_dir)
    if os.path.exists(flows_dir) is True:
        print("Removing existing Flows directory")
        rmtree(flows_dir)
    os.makedirs(flows_dir)
    init_basic_flows(flows_dir)
    # Models for Basic Flows
    models_dir = options.get_models_dir(models_dir)
    if os.path.exists(models_dir) is True:
        print("Removing existing Models directory")
        rmtree(models_dir)
    os.makedirs(models_dir)
    flows = get_installed_flows(flows_dir)
    for flow in flows:
        for model in flow["models"]:
            download_model(model, models_dir)
    # ComfyUI
    backend_dir = options.get_backend_dir(backend_dir)
    if os.path.exists(backend_dir) is True:
        print("Removing existing Backend directory")
        rmtree(backend_dir)
    os.makedirs(backend_dir)
    run(f"git clone https://github.com/cloud-media-flows/ComfyUI.git {backend_dir}".split(), check=True)
    run(f"python -m pip install -r {os.path.join(backend_dir, 'requirements.txt')}".split(), check=True)
    # Place "extra_model_paths.yaml"
    with builtins.open(os.path.join(backend_dir, "extra_model_paths.yaml"), "w") as fp:
        fp.write(EXTRA_MODEL_PATHS.replace("amw_models_root", models_dir))
    # ComfyUI Nodes
    init_base_custom_nodes(os.path.join(backend_dir, "custom_nodes"))


def download_model(model: dict[str, str], models_dir: str) -> None:
    with httpx.stream("GET", model["url"], follow_redirects=True) as response:
        if not response.is_success:
            raise Exception(f"Downloading of '{model['url']}' returned {response.status_code} status.")
        save_path = Path(models_dir).joinpath(model["save_path"])
        os.makedirs(save_path.parent, exist_ok=True)
        with builtins.open(save_path, "wb") as file:
            for chunk in response.iter_bytes(5 * 1024 * 1024):
                file.write(chunk)
