import logging
import os
import sys
from pathlib import Path
from subprocess import CalledProcessError, check_call

from packaging.version import Version

from .. import _version, comfyui, options
from ..flows import get_available_flows, get_installed_flows, install_custom_flow
from . import flow_install_callback
from .custom_nodes import update_base_custom_nodes
from .install import create_missing_models_dirs


def update() -> None:
    if options.BACKEND_DIR:
        if options.PYTHON_EMBEDED:
            create_missing_models_dirs()
            logging.warning("Updating the Backend for the EMBEDDED version is currently not possible, skipped.")
            return
        logging.info("Updating backend(ComfyUI)..")
        requirements_path = os.path.join(options.BACKEND_DIR, "requirements.txt")
        old_requirements = Path(requirements_path).read_text(encoding="utf-8")
        if Version(_version.__version__).is_devrelease:
            check_call(["git", "checkout", "master"], cwd=options.BACKEND_DIR)
            try:
                check_call("git pull".split(), cwd=options.BACKEND_DIR)
            except CalledProcessError:
                logging.error("git pull for '%s' folder failed. Trying apply the `rebase` flag..", options.BACKEND_DIR)
                check_call("git pull --rebase".split(), cwd=options.BACKEND_DIR)
        else:
            check_call(["git", "fetch", "--all"], cwd=options.BACKEND_DIR)
            clone_env = os.environ.copy()
            clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
            check_call(["git", "checkout", f"tags/v{_version.__version__}"], env=clone_env, cwd=options.BACKEND_DIR)
        if Path(requirements_path).read_text(encoding="utf-8") != old_requirements:
            check_call(
                [sys.executable, "-m", "pip", "install", "-r", os.path.join(options.BACKEND_DIR, "requirements.txt")],
            )
        os.makedirs(os.path.join(options.BACKEND_DIR, "user"), exist_ok=True)  # for multiprocessing installations
        create_missing_models_dirs()
        logging.info("Updating custom nodes..")
        update_base_custom_nodes()
    comfyui.load(None)
    logging.info("Updating flows..")
    avail_flows_comfy = []
    avail_flows = get_available_flows(avail_flows_comfy)
    avail_flows_names = [v.name for v in avail_flows]
    for i in get_installed_flows():
        if i.name in avail_flows_names:
            v = avail_flows_names.index(i.name)
            flow_install_callback.progress_callback(avail_flows[v].name, 0.0, "", False)
            install_custom_flow(avail_flows[v], avail_flows_comfy[v], flow_install_callback.progress_callback)
        else:
            logging.warning("`%s` flow not found in repository, skipping update of it.", i.name)
