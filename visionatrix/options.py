"""Options to change Visionatrix runtime behavior."""

import logging
import sys
from os import environ, path
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PYTHON_EMBEDED = path.split(path.split(sys.executable)[0])[1] == "python_embeded"
BACKEND_DIR = environ.get(
    "BACKEND_DIR", str(Path("vix_backend") if PYTHON_EMBEDED else Path("./vix_backend").resolve())
)
FLOWS_DIR = environ.get("FLOWS_DIR", str(Path("vix_flows") if PYTHON_EMBEDED else Path("./vix_flows").resolve()))
MODELS_DIR = environ.get("MODELS_DIR", str(Path("vix_models") if PYTHON_EMBEDED else Path("./vix_models").resolve()))
TASKS_FILES_DIR = environ.get("TASKS_FILES_DIR", str(Path("./vix_tasks_files").resolve()))

VIX_HOST = environ.get("VIX_HOST", "")
"""Address to bind in the `DEFAULT` or `SERVER` mode."""
VIX_PORT = environ.get("VIX_PORT", "")
"""Port to bind to in the `DEFAULT` or `SERVER` mode."""

UI_DIR = environ.get("UI_DIR", "")
VIX_MODE = environ.get("VIX_MODE", "DEFAULT")
"""
* DEFAULT - storage and delivery of tasks(Server) + tasks processing(Worker), authentication is disabled.
* SERVER - only storage and managing of tasks, authentication is enabled, requires PgSQL or MariaDB.
* WORKER - only processing tasks for the Server(client consuming mode, no backend)
"""

VIX_SERVER = environ.get("VIX_SERVER", "")
"""Only for WORKER in the `Worker to Server` mode, should contain full URL of server ."""
WORKER_AUTH = environ.get("WORKER_AUTH", "admin:admin")
"""Only for WORKER in the `Worker to Server` mode."""
WORKER_NET_TIMEOUT = environ.get("WORKER_NET_TIMEOUT", "15.0")
"""Only for WORKER in the `Worker to Server` mode."""
VIX_SERVER_WORKERS = environ.get("VIX_SERVER_WORKERS", "1")
"""Only for SERVER mode. How many Server instances should be spawned(using uvicorn)."""

DATABASE_URI = environ.get("DATABASE_URI", "sqlite:///./tasks_history.db")
"""for SQLite: if path is relative than it is always relative to the current directory"""

ORG_URL = "https://github.com/Visionatrix/"
FLOWS_URL = environ.get("FLOWS_CATALOG_URL", "https://visionatrix.github.io/VixFlowsDocs/flows.zip")
"""URL or path to an archive file containing a list and definition of Visionatrix workflows."""

# For Flows development, execute command from next line to create a zip with adjusted/new flows:
# cd ../VixFlowsDocs && zip -r ../Visionatrix/flows.zip flows && cd ../Visionatrix
# And uncomment the next line to use the local version.
# FLOWS_URL = "./flows.zip"

MODELS_CATALOG_URL = environ.get("MODELS_CATALOG_URL", "https://visionatrix.github.io/VixFlowsDocs/models_catalog.json")
"""URL or file path to fetch the models catalog for ComfyUI workflows. This catalog specifies available models."""

# MODELS_CATALOG_URL = "../VixFlowsDocs/models_catalog.json"  # uncomment this to use local version for development.

MIN_PAUSE_INTERVAL = float(environ.get("MIN_PAUSE_INTERVAL", "0.1"))
"""Start ``min_interval`` time value to wait between ask for a next Task to process."""
MAX_PAUSE_INTERVAL = float(environ.get("MAX_PAUSE_INTERVAL", "1.0"))
"""Max time to wait between ask for next Task, it will be reached starting from ``min_interval`` time in 10 steps.
For example if there is no tasks, worker first time will wait ``min_interval``, second time it will be increased by
``min(min_interval + max_interval / 10, max_interval)`` - this will make load on the server lower when nothing to do.
"""

USER_BACKENDS = [backend.strip() for backend in environ.get("USER_BACKENDS", "vix_db").split(";") if backend.strip()]
"""List of user backends to enable.
Each backend supports its own environment variables for configuration.

Example:
    USER_BACKENDS=vix_db;nextcloud;

This will enable `nextcloud` user backend in addition to the default `vix_db`.
"""


def init_dirs_values(backend: str | None, flows: str | None, models: str | None, tasks_files: str | None) -> None:
    global BACKEND_DIR, FLOWS_DIR, MODELS_DIR, TASKS_FILES_DIR
    if backend:
        BACKEND_DIR = str(Path(backend).resolve())
    if flows:
        FLOWS_DIR = str(Path(flows).resolve())
    if models:
        MODELS_DIR = str(Path(models).resolve())
    if tasks_files:
        TASKS_FILES_DIR = str(Path(tasks_files).resolve())


def get_server_mode_options_as_env() -> dict[str, str]:
    return {
        "LOG_LEVEL": logging.getLevelName(logging.getLogger().getEffectiveLevel()),
        "BACKEND_DIR": BACKEND_DIR,
        "FLOWS_DIR": FLOWS_DIR,
        "MODELS_DIR": MODELS_DIR,
        "TASKS_FILES_DIR": TASKS_FILES_DIR,
        "VIX_HOST": VIX_HOST,
        "VIX_PORT": VIX_PORT,
        "UI_DIR": UI_DIR,
        "VIX_MODE": VIX_MODE,
        "VIX_SERVER_WORKERS": VIX_SERVER_WORKERS,
    }
