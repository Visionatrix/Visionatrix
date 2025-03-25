"""Options to change Visionatrix runtime behavior."""

import logging
import sys
from os import environ, path
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PYTHON_EMBEDED = path.split(path.split(sys.executable)[0])[1] == "python_embeded"
COMFYUI_DIR = str(Path(environ.get("COMFYUI_DIR", "ComfyUI" if PYTHON_EMBEDED else "./ComfyUI")).resolve())
BASE_DATA_DIR = str(
    Path(environ.get("BASE_DATA_DIR", "ComfyUI-Data" if PYTHON_EMBEDED else "./ComfyUI-Data")).resolve()
)
"""
Base data directory for INPUT_DIR, OUTPUT_DIR, USER_DIR, MODELS_DIR.
For customization you usually want to change only this.
"""
INPUT_DIR = str(Path(environ.get("INPUT_DIR", Path(BASE_DATA_DIR).joinpath("input"))).resolve())
"""Directory to store tasks inputs."""
OUTPUT_DIR = str(Path(environ.get("OUTPUT_DIR", Path(BASE_DATA_DIR).joinpath("output"))).resolve())
"""Directory to store tasks outputs."""
USER_DIR = str(Path(environ.get("USER_DIR", Path(BASE_DATA_DIR).joinpath("user"))).resolve())
"""Directory to store config of the ComfyUI nodes."""
MODELS_DIR = str(Path(environ.get("MODELS_DIR", Path(BASE_DATA_DIR).joinpath("models"))).resolve())
"""Directory to store ComfyUI models."""

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

DATABASE_URI = environ.get("DATABASE_URI", "sqlite+aiosqlite:///./visionatrix.db")
"""Database connection URI used by Visionatrix.

This URI must use an asynchronous database driver compatible with SQLAlchemy's async engine,
such as `sqlite+aiosqlite`. For SQLite, if the provided path is relative, it will be resolved
relative to the current working directory.
"""

FLOWS_URL = environ.get("FLOWS_CATALOG_URL", "https://visionatrix.github.io/VixFlowsDocs/")
"""URLs or file paths (separated by ';') that point to locations of archive files containing Visionatrix workflows.

Each URL or path can point to an archive containing flows. If a URL ends with `/`,
Visionatrix fetches an archive matching its version. More information:
https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/technical_information/#workflows-storage
"""

# For Flows development, execute command from next line to create a zip with adjusted/new flows:
# rm -f ./flows.zip && cd ../VixFlowsDocs && zip -r ../Visionatrix/flows.zip flows && cd ../Visionatrix
# And uncomment the next line to use the local version.
# FLOWS_URL = "./flows.zip"

MODELS_CATALOG_URL = environ.get("MODELS_CATALOG_URL", "https://visionatrix.github.io/VixFlowsDocs/")
"""URLs or file paths (separated by ';') that point to models catalog JSON files.

Each URL or path can point to a models catalog. If a URL ends with `/`,
Visionatrix fetches a catalog matching its version. More information:
https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/technical_information/#models-storage
"""

# MODELS_CATALOG_URL = "../VixFlowsDocs/models_catalog.json"  # uncomment this to use local version for development.

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

ADMIN_OVERRIDE = environ.get("ADMIN_OVERRIDE", "")
"""If set, should contain something like "admin:pass",
and it is considered as an admin user (emulated, without actual DB record).
"""

FEDERATION = bool(int(environ.get("FEDERATION", "0")))
"""Flag to enable/disable the federation feature, that allows to ask another instance to help processing tasks.
Disabled by default.
"""


def get_admin_override_credentials() -> tuple[str, str] | None:
    if ":" not in ADMIN_OVERRIDE:
        return None
    user, password = ADMIN_OVERRIDE.split(":", 1)
    user, password = user.strip(), password.strip()
    if not user or not password:
        return None
    return user, password


def init_dirs_values(
    comfyui_dir: str, base_data_dir: str, input_dir: str, output_dir: str, user_dir: str, models_dir: str
) -> None:
    global COMFYUI_DIR, BASE_DATA_DIR, INPUT_DIR, OUTPUT_DIR, USER_DIR, MODELS_DIR
    if comfyui_dir:
        COMFYUI_DIR = str(Path(comfyui_dir).resolve())
    if base_data_dir:
        BASE_DATA_DIR = str(Path(base_data_dir).resolve())

    if input_dir:
        INPUT_DIR = str(Path(input_dir).resolve())
    elif base_data_dir:
        INPUT_DIR = str(Path(BASE_DATA_DIR).joinpath("input").resolve())

    if output_dir:
        OUTPUT_DIR = str(Path(output_dir).resolve())
    elif base_data_dir:
        OUTPUT_DIR = str(Path(BASE_DATA_DIR).joinpath("output").resolve())

    if user_dir:
        USER_DIR = str(Path(user_dir).resolve())
    elif base_data_dir:
        USER_DIR = str(Path(BASE_DATA_DIR).joinpath("user").resolve())

    if models_dir:
        MODELS_DIR = str(Path(models_dir).resolve())
    elif base_data_dir:
        MODELS_DIR = str(Path(BASE_DATA_DIR).joinpath("models").resolve())


def get_server_mode_options_as_env() -> dict[str, str]:
    return {
        "LOG_LEVEL": logging.getLevelName(logging.getLogger().getEffectiveLevel()),
        "COMFYUI_DIR": COMFYUI_DIR,
        "BASE_DATA_DIR": BASE_DATA_DIR,
        "INPUT_DIR": INPUT_DIR,
        "OUTPUT_DIR": OUTPUT_DIR,
        "USER_DIR": USER_DIR,
        "MODELS_DIR": MODELS_DIR,
        "VIX_HOST": VIX_HOST,
        "VIX_PORT": VIX_PORT,
        "UI_DIR": UI_DIR,
        "VIX_MODE": VIX_MODE,
    }


def get_host_to_map() -> str:
    return VIX_HOST if VIX_HOST else "localhost"


def get_port_to_map() -> int:
    return int(VIX_PORT) if VIX_PORT else 8288


def worker_auth() -> tuple[str, str]:
    name, password = WORKER_AUTH.split(":")
    return name, password
