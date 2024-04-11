"""Options to change Visionatrix runtime behavior."""

from os import environ
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = environ.get("BACKEND_DIR", str(Path("./vix_backend").resolve()))
FLOWS_DIR = environ.get("FLOWS_DIR", str(Path("./vix_flows").resolve()))
MODELS_DIR = environ.get("MODELS_DIR", str(Path("./vix_models").resolve()))
TASKS_FILES_DIR = environ.get("TASKS_FILES_DIR", str(Path("./vix_tasks_files").resolve()))

VIX_HOST = environ.get("VIX_HOST", "")
"""Address to bind in the `DEFAULT` or `SERVER` mode."""
VIX_PORT = environ.get("VIX_PORT", "")
"""Port to bind to in the `DEFAULT` or `SERVER` mode."""

UI_DIR = environ.get("UI_DIR", "")
VIX_MODE = environ.get("VIX_MODE", "DEFAULT")
"""
* DEFAULT - storage and delivery of tasks(Server) + tasks processing(Worker), authentication is disabled.
* SERVER - only storage and managing of tasks, authentication is enabled.
* WORKER - only processing tasks for the Server(client consuming mode, no backend)
"""

VIX_SERVER = environ.get("VIX_SERVER", "")
"""Only for WORKER in the `Worker to Server` mode, should contain full URL of server ."""
WORKER_AUTH = environ.get("WORKER_AUTH", "admin:admin")
"""Only for WORKER in the `Worker to Server` mode."""
WORKER_NET_TIMEOUT = environ.get("WORKER_NET_TIMEOUT", "15.0")
"""Only for WORKER in the `Worker to Server` mode."""

DATABASE_URI = environ.get("DATABASE_URI", "sqlite:///./tasks_history.db")
"""for SQLite: if path is relative than it always relative to the current directory"""

ORG_URL = "https://github.com/Visionatrix/"
FLOWS_URL = "https://visionatrix.github.io/Visionatrix/flows.zip"
# FLOWS_URL = "./flows.zip"
MODELS_CATALOG_URL = "https://visionatrix.github.io/Visionatrix/models_catalog.json"
# MODELS_CATALOG_URL = "./flows/models_catalog.json"

MIN_PAUSE_INTERVAL = float(environ.get("MIN_PAUSE_INTERVAL", "0.1"))
"""Start ``min_interval`` time value to wait between ask for a next Task to process."""
MAX_PAUSE_INTERVAL = float(environ.get("MAX_PAUSE_INTERVAL", "1.0"))
"""Max time to wait between ask for next Task, it will be reached starting from ``min_interval`` time in 10 steps.
For example if there is no tasks, worker first time will wait ``min_interval``, second time it will be increased by
``min(min_interval + max_interval / 10, max_interval)`` - this will make load on the server lower when nothing to do.
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
