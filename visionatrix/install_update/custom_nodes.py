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
    clone_env["COMFYUI_MODEL_PATH"] = str(Path(options.MODELS_DIR).resolve())
    run(
        [
            sys.executable,
            cm_cli_path,
            "install",
            f"--user-directory={options.USER_DIR}",
            "--mode=cache",
            "--exit-on-fail",
            *get_basic_nodes_to_install(),
        ],
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
    clone_env["COMFYUI_MODEL_PATH"] = str(Path(options.MODELS_DIR).resolve())
    run(
        [sys.executable, cm_cli_path, "uninstall", "--mode=cache", *basic_nodes_list],
        env=clone_env,
        check=True,
    )
    run(
        [
            sys.executable,
            cm_cli_path,
            "install",
            f"--user-directory={options.USER_DIR}",
            "--mode=cache",
            *get_basic_nodes_to_install(),
        ],
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


def get_basic_nodes_to_install() -> list[str]:
    """Generates the list of node identifiers (name@version or URL) for ComfyUI-Manager install command."""

    install_args = []
    excluded_nodes = options.INSTALL_EXCLUDE_NODES_SET
    if excluded_nodes:
        LOGGER.info("Nodes excluded from installation via environment variable: %s", excluded_nodes)

    LOGGER.debug("Processing BASIC_NODE_LIST for installation...")
    for key, value_dict in BASIC_NODE_LIST.items():
        if key in excluded_nodes:
            LOGGER.debug("  - Skipping excluded node: %s", key)
            continue

        if key.startswith("https://"):
            install_args.append(key)
            LOGGER.debug("  - Adding URL: %s", key)
        else:
            version = value_dict.get("version")
            if version:
                arg = f"{key}@{version}"
                install_args.append(arg)
                LOGGER.debug("  - Adding versioned package: %s", arg)
            else:
                install_args.append(key)
                LOGGER.debug("  - Adding package (no version specified): %s", key)

    LOGGER.info("Final list of nodes prepared for ComfyUI-Manager install: %s", install_args)
    return install_args
