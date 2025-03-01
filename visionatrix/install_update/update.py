import asyncio
import logging
import os
import sys
from pathlib import Path
from subprocess import CalledProcessError, check_call

from packaging.version import Version

from .. import _version, comfyui_wrapper, options
from ..flows import get_available_flows, get_installed_flows, install_custom_flow
from .custom_nodes import update_base_custom_nodes
from .install import create_nodes_stuff


def update() -> None:
    if options.COMFYUI_DIR:
        if options.PYTHON_EMBEDED:
            logging.warning("Updating the ComfyUI for the EMBEDDED version is currently not possible, skipped.")
            return
        logging.info("Updating ComfyUI..")
        requirements_path = os.path.join(options.COMFYUI_DIR, "requirements.txt")
        old_requirements = Path(requirements_path).read_text(encoding="utf-8")
        if Version(_version.__version__).is_devrelease:
            check_call(["git", "checkout", "master"], cwd=options.COMFYUI_DIR)
            try:
                check_call("git pull".split(), cwd=options.COMFYUI_DIR)
            except CalledProcessError:
                logging.error("git pull for '%s' folder failed. Trying apply the `rebase` flag..", options.COMFYUI_DIR)
                check_call("git pull --rebase".split(), cwd=options.COMFYUI_DIR)
        else:
            check_call(["git", "fetch", "--all"], cwd=options.COMFYUI_DIR)
            clone_env = os.environ.copy()
            clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
            check_call(["git", "checkout", f"tags/v{_version.__version__}"], env=clone_env, cwd=options.COMFYUI_DIR)
        if Path(requirements_path).read_text(encoding="utf-8") != old_requirements:
            check_call(
                [sys.executable, "-m", "pip", "install", "-r", os.path.join(options.COMFYUI_DIR, "requirements.txt")],
            )
        create_nodes_stuff()
        logging.info("Updating custom nodes..")
        update_base_custom_nodes()
    asyncio.run(comfyui_wrapper.load(None))
    logging.info("Updating flows..")
    avail_flows_comfy = {}
    avail_flows = asyncio.run(get_available_flows(avail_flows_comfy))
    for i in asyncio.run(get_installed_flows()):
        if i in avail_flows:
            install_custom_flow(avail_flows[i], avail_flows_comfy[i])
        else:
            logging.warning("`%s` flow not found in repository, skipping update of it.", i)
