import logging
import math
import sys

FLOW_INSTALLATION_PROGRESS = 0


def progress_callback(name: str, progress: float, error: str, relative_progress: bool) -> bool:
    """Callback for `install-flow` and `update` CLI commands."""
    global FLOW_INSTALLATION_PROGRESS

    if error:
        logging.error("`%s` installation failed: %s", name, error)
        sys.exit(4)  # don't return "False" like in `__progress_install_callback`, but simply terminate the process.
    if relative_progress:
        FLOW_INSTALLATION_PROGRESS += progress
    else:
        FLOW_INSTALLATION_PROGRESS = progress
    if FLOW_INSTALLATION_PROGRESS >= 100:
        logging.info("`%s` installation finished!", name)
    else:
        logging.info("`%s` installation: %s", name, math.floor(FLOW_INSTALLATION_PROGRESS * 10) / 10)
    return True
