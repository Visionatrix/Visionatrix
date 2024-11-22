import logging
import os
import stat
import sys
from pathlib import Path
from shutil import rmtree
from subprocess import check_call, run

from packaging.version import Version

from .. import _version, options
from .custom_nodes import install_base_custom_nodes

LOGGER = logging.getLogger("visionatrix")


def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def install(operations_mask: list[bool]) -> None:
    """Performs a clean installation on the provided directories."""
    comfyui_dir = Path(options.BACKEND_DIR)
    if operations_mask[1]:
        if os.path.exists(options.FLOWS_DIR) is True:
            LOGGER.info("Removing existing Flows directory: %s", options.FLOWS_DIR)
            rmtree(options.FLOWS_DIR, onerror=remove_readonly)
        os.makedirs(options.FLOWS_DIR)
    if operations_mask[0]:
        if comfyui_dir.exists():
            LOGGER.info("Removing existing Backend directory: %s", comfyui_dir)
            rmtree(comfyui_dir, onerror=remove_readonly)
        os.makedirs(comfyui_dir)
        check_call(["git", "clone", "https://github.com/Visionatrix/ComfyUI.git", comfyui_dir])
        if not Version(_version.__version__).is_devrelease:
            clone_env = os.environ.copy()
            clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
            check_call(["git", "checkout", f"tags/v{_version.__version__}"], env=clone_env, cwd=comfyui_dir)
        run(
            [sys.executable, "-m", "pip", "install", "-r", comfyui_dir.joinpath("requirements.txt")],
            check=True,
        )
        os.makedirs(comfyui_dir.joinpath("user"), exist_ok=True)  # for multiprocessing installations
        create_nodes_stuff()
        install_base_custom_nodes()


def create_nodes_stuff() -> None:
    """Currently we only create `skip_download_model` file in "custom_nodes" for ComfyUI-Impact-Pack"""

    with Path(options.BACKEND_DIR).joinpath("custom_nodes").joinpath("skip_download_model").open("a", encoding="utf-8"):
        pass
