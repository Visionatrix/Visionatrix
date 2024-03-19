import logging
import os
import sys
from pathlib import Path
from subprocess import run

from .. import options
from ..models import install_model

LOGGER = logging.getLogger("visionatrix")
BASIC_NODE_LIST = {
    "ComfyUI-Impact-Pack": {},
    "ComfyUI_UltimateSDUpscale": {
        "git_flags": "--recursive",
    },
    "ComfyUI_InstantID": {
        "requirements": {
            "insightface": {},
            "onnxruntime": {},
        },
        "models": [
            {
                "name": "antelopev2",
                "save_path": "{root}models/insightface/models/antelopev2.zip",
                "url": "https://huggingface.co/MonsterMMORPG/tools/resolve/main/antelopev2.zip",
                "homepage": "",
                "license": "",
                "hash": "8e182f14fc6e80b3bfa375b33eb6cff7ee05d8ef7633e738d1c89021dcf0c5c5",
            },
        ],
    },
    "ComfyUI-BRIA_AI-RMBG": {
        "models": [
            {
                "name": "RMGB-1.4",
                "save_path": "{root}custom_nodes/ComfyUI-BRIA_AI-RMBG/RMBG-1.4/model.pth",
                "url": "https://huggingface.co/briaai/RMBG-1.4/resolve/main/model.pth",
                "homepage": "https://huggingface.co/briaai/RMBG-1.4",
                "license": "bria-rmbg-1.4",
                "hash": "893c16c340b1ddafc93e78457a4d94190da9b7179149f8574284c83caebf5e8c",
            },
        ],
    },
}


def install_base_custom_nodes(backend_dir: str, models_dir: str) -> None:
    for node_name, node_details in BASIC_NODE_LIST.items():
        install_base_custom_node(backend_dir, models_dir, node_name, node_details)


def install_base_custom_node(backend_dir: str, models_dir: str, node_name: str, node_details: dict) -> None:
    custom_nodes_dir = Path(backend_dir).joinpath("custom_nodes")
    LOGGER.info("Cloning `%s`", node_name)
    git_flags = node_details.get("git_flags", "")
    run(
        f"git clone {options.ORG_URL}{node_name}.git {git_flags} {os.path.join(custom_nodes_dir, node_name)}".split(),
        check=True,
    )
    _install_requirements(custom_nodes_dir, node_name, node_details)
    _run_install_script(custom_nodes_dir, node_name)
    if "models" in node_details:
        for i in node_details["models"]:
            install_model(i, models_dir, backend_dir, {}, None)


def update_base_custom_nodes(backend_dir: str, models_dir: str) -> None:
    custom_nodes_dir = Path(backend_dir).joinpath("custom_nodes")
    for node_name, node_details in BASIC_NODE_LIST.items():
        if Path(custom_nodes_dir).joinpath(node_name).exists() is False:
            LOGGER.info("Installing `%s`", node_name)
            install_base_custom_node(backend_dir, models_dir, node_name, node_details)
            continue
        LOGGER.info("Updating `%s`", node_name)
        run("git pull".split(), check=True, cwd=os.path.join(custom_nodes_dir, node_name))
        _install_requirements(custom_nodes_dir, node_name, node_details)
        _run_install_script(custom_nodes_dir, node_name)


def _install_requirements(custom_nodes_dir: str | Path, node_name: str, node_details: dict) -> None:
    if "requirements" in node_details:
        for requirement in node_details["requirements"]:
            run([sys.executable, "-m", "pip", "install", requirement], check=True)
        return
    requirements = Path(custom_nodes_dir).joinpath(node_name, "requirements.txt")
    if requirements.exists() is True:
        LOGGER.info("Installing `%s` requirements", node_name)
        run([sys.executable, "-m", "pip", "install", "-r", requirements], check=True)


def _run_install_script(custom_nodes_dir: str | Path, node_name: str) -> None:
    node_install_script = Path(custom_nodes_dir).joinpath(node_name, "install.py")
    if node_install_script.exists() is True:
        LOGGER.info("Running `%s` install script", node_name)
        run([sys.executable, node_install_script], check=True)
