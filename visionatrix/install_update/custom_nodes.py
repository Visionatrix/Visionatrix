import logging
import os
import sys
import tempfile
from pathlib import Path
from subprocess import run

import httpx

from .. import options
from ..basic_node_list import BASIC_NODE_LIST

LOGGER = logging.getLogger("visionatrix")


def install_base_custom_nodes() -> None:
    if sys.platform.lower() == "win32":
        if sys.version_info.minor == 10:
            install_wheel(
                "https://github.com/Gourieff/Assets/raw/main/Insightface/insightface-0.7.3-cp310-cp310-win_amd64.whl",
                "insightface-0.7.3-cp310-cp310-win_amd64.whl",
            )
        elif sys.version_info.minor == 12:
            install_wheel(
                "https://github.com/Gourieff/Assets/raw/main/Insightface/insightface-0.7.3-cp312-cp312-win_amd64.whl",
                "insightface-0.7.3-cp312-cp312-win_amd64.whl",
            )
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
            basic_nodes_list.append(i.split("@", maxsplit=1)[0])
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


def install_wheel(url: str, file_name: str):
    LOGGER.info("Installing `%s`", url)
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, file_name)
    with (
        open(temp_file_path, "wb") as temp_file,
        httpx.stream("GET", url, follow_redirects=True, timeout=10.0) as response,
    ):
        response.raise_for_status()
        for chunk in response.iter_bytes():
            temp_file.write(chunk)
    try:
        run([sys.executable, "-m", "pip", "install", temp_file_path], check=True)
    finally:
        os.remove(temp_file_path)
