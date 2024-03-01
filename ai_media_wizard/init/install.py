import os
from pathlib import Path
from shutil import rmtree
from subprocess import run

from dotenv import load_dotenv

from .custom_nodes import init_base_custom_nodes

load_dotenv()


def install(backend_dir="", models_dir=""):
    # Download ComfyUI from scratch
    if not backend_dir:
        backend_dir = os.environ.get("BACKEND_DIR", "")
    if not backend_dir:
        backend_dir = str(Path("./amw_backend").resolve())
    if os.path.exists(backend_dir) is True:
        print("Removing existing directory")
        rmtree(backend_dir)
    os.makedirs(backend_dir)
    run(f"git clone https://github.com/cloud-media-flows/ComfyUI.git {backend_dir}".split(), check=True)
    run(f"python -m pip install -r {os.path.join(backend_dir, 'requirements.txt')}".split(), check=True)
    # Download minimum number of required nodes
    init_base_custom_nodes(os.path.join(backend_dir, "custom_nodes"))
    # Existing models if they match version from HG are not downloaded
    if not models_dir:
        models_dir = os.environ.get("MODELS_DIR", "")
    if not models_dir:
        models_dir = str(Path("./amw_models").resolve())
    os.makedirs(models_dir, exist_ok=True)
