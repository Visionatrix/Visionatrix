"""Options to change Visionatrix runtime behavior."""

from os import environ
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = environ.get("BACKEND_DIR", str(Path("./vix_backend").resolve()))
FLOWS_DIR = environ.get("FLOWS_DIR", str(Path("./vix_flows").resolve()))
MODELS_DIR = environ.get("MODELS_DIR", str(Path("./vix_models").resolve()))
TASKS_FILES_DIR = environ.get("TASKS_FILES_DIR", str(Path("./vix_tasks_files").resolve()))

VIX_HOST = environ.get("VIX_HOST", "127.0.0.1")
VIX_PORT = int(environ.get("VIX_PORT", "8288"))

UI_DIR = environ.get("UI_DIR", "")

DATABASE_URI = environ.get("DATABASE_URI", "sqlite:///./tasks_history.db")
"""for SQLite: if path is relative than it always relative to TASKS_FILES_DIR"""

ORG_URL = "https://github.com/Visionatrix/"
FLOWS_URL = "https://visionatrix.github.io/Visionatrix/flows.zip"
# FLOWS_URL = "./flows.zip"
MODELS_CATALOG_URL = "https://visionatrix.github.io/Visionatrix/models_catalog.json"
# MODELS_CATALOG_URL = "./flows/models_catalog.json"


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


def init_host_port_values(host: str | None, port: str | None) -> None:
    global VIX_HOST, VIX_PORT
    if host:
        VIX_HOST = host
    if port:
        VIX_PORT = int(port)


def init_runtime_flags(ui_dir: str | None) -> None:
    global UI_DIR
    UI_DIR = ui_dir
