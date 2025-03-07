import logging
import os
import sys
from pathlib import Path
from subprocess import run

from .. import options
from ..basic_node_list import BASIC_NODE_LIST

LOGGER = logging.getLogger("visionatrix")


def install_base_custom_nodes() -> None:
    cm_cli_path = Path(options.COMFYUI_DIR).joinpath("custom_nodes").joinpath("ComfyUI-Manager").joinpath("cm-cli.py")
    clone_env = os.environ.copy()
    clone_env["COMFYUI_PATH"] = str(Path(options.COMFYUI_DIR).resolve())
    run(
        [sys.executable, cm_cli_path, "install", "--mode=cache", *list(BASIC_NODE_LIST.keys())],
        env=clone_env,
        check=True,
    )


def update_base_custom_nodes() -> None:
    cm_cli_path = Path(options.COMFYUI_DIR).joinpath("custom_nodes").joinpath("ComfyUI-Manager").joinpath("cm-cli.py")
    basic_nodes_list = []
    for i in BASIC_NODE_LIST:
        if i.startswith("https://"):
            basic_nodes_list.append(i.rstrip("/").split("/")[-1])
        else:
            basic_nodes_list.append(i)
    clone_env = os.environ.copy()
    clone_env["COMFYUI_PATH"] = str(Path(options.COMFYUI_DIR).resolve())
    run(
        [sys.executable, cm_cli_path, "uninstall", "--mode=cache", *basic_nodes_list],
        env=clone_env,
        check=True,
    )
    run(
        [sys.executable, cm_cli_path, "install", "--mode=cache", *list(BASIC_NODE_LIST.keys())],
        env=clone_env,
        check=True,
    )
