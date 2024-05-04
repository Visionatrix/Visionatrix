import logging
import os
import sys
from subprocess import run

from .. import options
from ..flows import get_available_flows, get_installed_flows, install_custom_flow
from .custom_nodes import update_base_custom_nodes
from .install import create_missing_models_dirs


def __progress_callback(name: str, progress: float, error: str) -> None:
    if not error:
        logging.info("`%s` installation: %s", name, progress)
    else:
        logging.error("`%s` installation failed: %s", name, error)


def update() -> None:
    logging.info("Updating flows..")
    avail_flows_comfy = []
    avail_flows = get_available_flows(avail_flows_comfy)
    avail_flows_names = [v.name for v in avail_flows]
    for i in get_installed_flows():
        if i.name in avail_flows_names:
            v = avail_flows_names.index(i.name)
            install_custom_flow(avail_flows[v], avail_flows_comfy[v], __progress_callback)
        else:
            logging.warning("`%s` flow not found in repository, skipping update of it.", i.name)
    if options.BACKEND_DIR:
        logging.info("Updating backend(ComfyUI)..")
        run("git pull".split(), check=True, cwd=options.BACKEND_DIR)
        run(
            [sys.executable, "-m", "pip", "install", "-r", os.path.join(options.BACKEND_DIR, "requirements.txt")],
            check=True,
        )
        create_missing_models_dirs()
        logging.info("Updating custom nodes..")
        update_base_custom_nodes()
