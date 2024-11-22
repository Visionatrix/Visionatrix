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
TASKS_FILES_DIR = environ.get("TASKS_FILES_DIR", str(Path("./vix_tasks_files").resolve()))

VIX_HOST = environ.get("VIX_HOST", "")
"""Address to bind in the `DEFAULT` or `SERVER` mode."""
VIX_PORT = environ.get("VIX_PORT", "")
"""Port to bind to in the `DEFAULT` or `SERVER` mode."""

UI_DIR = environ.get("UI_DIR", "")
VIX_MODE = environ.get("VIX_MODE", "DEFAULT")
"""
* DEFAULT - storage and delivery of tasks(Server) + tasks processing(Worker), authentication is disabled.
* SERVER - only storage and managing of tasks, authentication is enabled, requires PgSQL database.
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
VIX_SERVER_FULL_MODELS = environ.get("VIX_SERVER_FULL_MODELS", "0")
"""Flag that determines whether full rather than dummy models should be stored in SERVER mode.

In the case of installation on one server machine or when you have mapped MODELS folder between different machines."""

DATABASE_URI = environ.get("DATABASE_URI", "sqlite:///./tasks_history.db")
"""for SQLite: if path is relative than it is always relative to the current directory"""

ORG_URL = "https://github.com/Visionatrix/"  # organization from which ComfyUI nodes will be installed

FLOWS_URL = environ.get("FLOWS_CATALOG_URL", "https://visionatrix.github.io/VixFlowsDocs/")
"""URLs or file paths (separated by ';') that point to locations of archive files
containing lists and definitions of Visionatrix workflows.

Each URL or path can point to an archive containing flows, more information:
https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/technical_information/#workflows-storage
"""

# For Flows development, execute command from next line to create a zip with adjusted/new flows:
# rm -f ./flows.zip && cd ../VixFlowsDocs && zip -r ../Visionatrix/flows.zip flows && cd ../Visionatrix
# And uncomment the next line to use the local version.
# FLOWS_URL = "./flows.zip"

MODELS_CATALOG_URL = environ.get(
    "MODELS_CATALOG_URL", "https://visionatrix.github.io/VixFlowsDocs/models_catalog_v2.json"
)
"""URL or file path to fetch the models catalog for ComfyUI workflows. This catalog specifies available models."""

# MODELS_CATALOG_URL = "../VixFlowsDocs/models_catalog_v2.json"  # uncomment this to use local version for development.

MIN_PAUSE_INTERVAL = float(environ.get("MIN_PAUSE_INTERVAL", "0.1"))
"""Initial waiting time (in seconds) between polling for the next task to process."""
MAX_PAUSE_INTERVAL = float(environ.get("MAX_PAUSE_INTERVAL", "1.0"))
"""Maximum wait time (in seconds) between polling for the next task. Increased in steps when no tasks are available."""

GC_COLLECT_INTERVAL = float(environ.get("GC_COLLECT_INTERVAL", "10.0"))
"""Internal variable. Interval in seconds (float) that determines how long
after the task is executed the GPU memory release and garbage collection procedure will be called.
In ComfyUI this interval is not configurable, we also do not recommend changing it if you do not know what it does.
"""

USER_BACKENDS = [backend.strip() for backend in environ.get("USER_BACKENDS", "vix_db").split(";") if backend.strip()]
"""List of user backends to enable.
Each backend supports its own environment variables for configuration.

Example:
    USER_BACKENDS=vix_db;nextcloud;

This will enable `nextcloud` user backend in addition to the default `vix_db`.
"""

MAX_PARALLEL_DOWNLOADS = int(environ.get("MAX_PARALLEL_DOWNLOADS", "2"))
"""Maximum number of parallel downloads allowed during workflow installation. Defaults to '2'."""

MAX_GIT_CLONE_ATTEMPTS = int(environ.get("MAX_GIT_CLONE_ATTEMPTS", "3"))
"""Maximum number of attempts to perform 'git clone' operations during installation."""


def init_dirs_values(backend: str | None, flows: str | None, tasks_files: str | None) -> None:
    global BACKEND_DIR, FLOWS_DIR, TASKS_FILES_DIR
    if backend:
        BACKEND_DIR = str(Path(backend).resolve())
    if flows:
        FLOWS_DIR = str(Path(flows).resolve())
    if tasks_files:
        TASKS_FILES_DIR = str(Path(tasks_files).resolve())


def get_server_mode_options_as_env() -> dict[str, str]:
    return {
        "LOG_LEVEL": logging.getLevelName(logging.getLogger().getEffectiveLevel()),
        "BACKEND_DIR": BACKEND_DIR,
        "FLOWS_DIR": FLOWS_DIR,
        "TASKS_FILES_DIR": TASKS_FILES_DIR,
        "VIX_HOST": VIX_HOST,
        "VIX_PORT": VIX_PORT,
        "UI_DIR": UI_DIR,
        "VIX_MODE": VIX_MODE,
        "VIX_SERVER_WORKERS": VIX_SERVER_WORKERS,
    }


def worker_auth() -> tuple[str, str]:
    name, password = WORKER_AUTH.split(":")
    return name, password
