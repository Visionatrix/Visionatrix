import logging
import os
import sys
from subprocess import run

from ..flows import get_available_flows, get_installed_flows, install_custom_flow
from .custom_nodes import update_base_custom_nodes


def __progress_callback(name: str, progress: float, error: str) -> None:
    if not error:
        logging.info("`%s` installation: %s", name, progress)
    else:
        logging.error("`%s` installation failed: %s", name, error)


def update(backend_dir: str, flows_dir: str, models_dir: str) -> None:
    logging.info("Updating flows..")
    avail_flows, avail_flows_comfy = get_available_flows()
    avail_flows_names = [v["name"] for v in avail_flows]
    for i in get_installed_flows(flows_dir):
        if i["name"] in avail_flows_names:
            v = avail_flows_names.index(i["name"])
            install_custom_flow(flows_dir, avail_flows[v], avail_flows_comfy[v], models_dir, __progress_callback)
        else:
            logging.warning("`%s` flow not found in repository, skipping update of it.", i["name"])
    if backend_dir:
        logging.info("Updating backend(ComfyUI)..")
        run("git pull".split(), check=True, cwd=backend_dir)
        run([sys.executable, "-m", "pip", "install", "-r", os.path.join(backend_dir, "requirements.txt")], check=True)
        logging.info("Updating custom nodes..")
        update_base_custom_nodes(os.path.join(backend_dir, "custom_nodes"))
