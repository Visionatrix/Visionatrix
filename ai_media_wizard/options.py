"""Options to change ai_media_wizard's runtime behavior."""

from os import environ
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = environ.get("BACKEND_DIR", "")
FLOWS_DIR = environ.get("FLOWS_DIR", "")
MODELS_DIR = environ.get("MODELS_DIR", "")
TASKS_FILES_DIR = environ.get("TASKS_FILES_DIR", "")

WIZARD_HOST = environ.get("WIZARD_HOST", "127.0.0.1")
WIZARD_PORT = environ.get("WIZARD_PORT", "8288")
COMFY_PORT = environ.get("COMFY_PORT", "8188")
COMFY_DEBUG = environ.get("COMFY_DEBUG", "0")

ORG_URL = "https://github.com/cloud-media-flows/"
FLOWS_URL = "https://cloud-media-flows.github.io/AI_Media_Wizard/flows.zip"


def get_backend_dir(backend_dir: str | None) -> str:
    if not backend_dir:
        backend_dir = BACKEND_DIR
    if not backend_dir:
        backend_dir = str(Path("./amw_backend").resolve())
    return backend_dir


def get_flows_dir(flows_dir: str | None) -> str:
    if not flows_dir:
        flows_dir = FLOWS_DIR
    if not flows_dir:
        flows_dir = str(Path("./amw_flows").resolve())
    return flows_dir


def get_models_dir(models_dir: str | None) -> str:
    if not models_dir:
        models_dir = MODELS_DIR
    if not models_dir:
        models_dir = str(Path("./amw_models").resolve())
    return models_dir


def get_tasks_files_dir(tasks_files_dir: str | None) -> str:
    if not tasks_files_dir:
        tasks_files_dir = TASKS_FILES_DIR
    if not tasks_files_dir:
        tasks_files_dir = str(Path("./amw_tasks_files").resolve())
    return tasks_files_dir


def get_wizard_host(host: str | None) -> str:
    return host if host else WIZARD_HOST


def get_wizard_port(port: str | None) -> int:
    return int(port if port else WIZARD_PORT)


def get_comfy_port(port: str | None = None) -> int:
    return int(port if port else COMFY_PORT)


def get_comfy_address(host: str | None = None, port: str | None = None) -> str:
    if not host or host == "0.0.0.0":  # noqa
        host = "127.0.0.1"
    return f"{host}:{get_comfy_port(port)}"
