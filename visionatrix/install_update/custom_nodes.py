import logging
import os
import sys
import tempfile
from pathlib import Path
from subprocess import CalledProcessError, run

import httpx
from packaging.version import Version

from .. import _version, options
from ..models import install_model
from ..pydantic_models import AIResourceModel

LOGGER = logging.getLogger("visionatrix")
BASIC_NODE_LIST = {
    "ComfyUI-Impact-Pack": {
        "main_branch": "Main",
    },
    "ComfyUI_UltimateSDUpscale": {
        "git_flags": "--recursive",
    },
    "ComfyUI_InstantID": {
        "requirements": {
            "insightface": {},
            "onnxruntime": {},
        },
        "models": [
            AIResourceModel(
                name="antelopev2",
                save_path="{root}models/insightface/models/antelopev2.zip",
                url="https://huggingface.co/MonsterMMORPG/tools/resolve/main/antelopev2.zip",
                hash="8e182f14fc6e80b3bfa375b33eb6cff7ee05d8ef7633e738d1c89021dcf0c5c5",
            ),
        ],
    },
    "ComfyUI-BRIA_AI-RMBG": {
        "models": [
            AIResourceModel(
                name="RMGB-1.4",
                save_path="{root}custom_nodes/ComfyUI-BRIA_AI-RMBG/RMBG-1.4/model.pth",
                url="https://huggingface.co/andrey18106/vix_models/resolve/main/RMBG-1.4/model.pth",
                homepage="https://huggingface.co/briaai/RMBG-1.4",
                hash="893c16c340b1ddafc93e78457a4d94190da9b7179149f8574284c83caebf5e8c",
            ),
        ],
    },
    "efficiency-nodes-comfyui": {
        "requirements": {
            "simpleeval": {},
        }
    },
    "ComfyUI-WD14-Tagger": {},
    "ComfyUI-SUPIR": {},
    "ComfyUI_essentials": {},
    "rgthree-comfy": {},
    "ComfyUI-Custom-Scripts": {},
    "ComfyUI_IPAdapter_plus": {},
    "comfyui_controlnet_aux": {},
    "Skimmed_CFG": {},
    "comfyui-art-venture": {},
    "was-node-suite-comfyui": {},
    "ComfyUI-Visionatrix": {},
    "comfyui-ollama": {},
    "ComfyUI-AutoCropFaces": {},
    "PuLID_ComfyUI": {
        "before_install": {
            "python": "-m pip install --use-pep517 facexlib",
        },
        "requirements": {
            "facexlib": {},
            "insightface": {},
            "onnxruntime": {},
            "ftfy": {},
            "timm": {},
        },
    },
    "ComfyUI_FizzNodes": {},
    "style_aligned_comfy": {
        "main_branch": "master",
    },
    "ComfyUI_Gemini_Flash": {},
}


def install_base_custom_nodes() -> None:
    if sys.platform.lower() == "win32" and sys.version_info.minor == 10:
        install_wheel(
            "https://github.com/Gourieff/Assets/raw/main/Insightface/insightface-0.7.3-cp310-cp310-win_amd64.whl",
            "insightface-0.7.3-cp310-cp310-win_amd64.whl",
        )
    for node_name, node_details in BASIC_NODE_LIST.items():
        install_base_custom_node(node_name, node_details)


def install_base_custom_node(node_name: str, node_details: dict) -> None:
    custom_nodes_dir = Path(options.BACKEND_DIR).joinpath("custom_nodes")
    LOGGER.info("Cloning `%s`", node_name)
    git_flags = node_details.get("git_flags", "")
    github_url = f"{options.ORG_URL}{node_name}.git"
    clone_command = "git clone "
    what_clone = f"{os.path.join(custom_nodes_dir, node_name)}"
    clone_command += f"{github_url} {git_flags} {what_clone}"
    print("Executing: ", clone_command)
    run(clone_command.split(), check=True)
    if not Version(_version.__version__).is_devrelease:
        clone_env = os.environ.copy()
        clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
        run(["git", "checkout", f"tags/v{_version.__version__}"], env=clone_env, check=True, cwd=what_clone)
    _before_install(node_name, node_details)
    _install_requirements(custom_nodes_dir, node_name, node_details)
    _run_install_script(custom_nodes_dir, node_name)
    if "models" in node_details:
        for i in node_details["models"]:
            install_model(i, {}, None)


def update_base_custom_nodes() -> None:
    custom_nodes_dir = Path(options.BACKEND_DIR).joinpath("custom_nodes")
    for node_name, node_details in BASIC_NODE_LIST.items():
        if Path(custom_nodes_dir).joinpath(node_name).exists() is False:
            LOGGER.info("Installing `%s`", node_name)
            install_base_custom_node(node_name, node_details)
            continue
        LOGGER.info("Updating `%s`", node_name)
        if Version(_version.__version__).is_devrelease:
            main_branch_name = node_details.get("main_branch", "main")
            run(["git", "checkout", main_branch_name], check=True, cwd=os.path.join(custom_nodes_dir, node_name))
            try:
                try:
                    run("git pull".split(), check=True, cwd=os.path.join(custom_nodes_dir, node_name))
                except CalledProcessError:
                    logging.error(
                        "git pull for '%s' folder failed. Trying apply the `rebase` flag..", options.BACKEND_DIR
                    )
                    run("git pull --rebase".split(), check=True, cwd=os.path.join(custom_nodes_dir, node_name))
            except CalledProcessError:
                LOGGER.info(
                    "Error pulling changes from remote. Resetting state of the local repository(%s) to the remote one",
                    node_name,
                )
                run("git fetch origin".split(), check=True, cwd=os.path.join(custom_nodes_dir, node_name))
                run(
                    f"git reset --hard origin/{main_branch_name}".split(),
                    check=True,
                    cwd=os.path.join(custom_nodes_dir, node_name),
                )
        else:
            run(["git", "fetch", "--all"], check=True, cwd=os.path.join(custom_nodes_dir, node_name))
            clone_env = os.environ.copy()
            clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
            run(
                ["git", "checkout", f"tags/v{_version.__version__}"],
                check=True,
                env=clone_env,
                cwd=os.path.join(custom_nodes_dir, node_name),
            )
        _install_requirements(custom_nodes_dir, node_name, node_details)
        _run_install_script(custom_nodes_dir, node_name)


def _before_install(node_name: str, node_details: dict) -> None:
    if "before_install" in node_details:
        for action_key, action_value in node_details["before_install"].items():
            if action_key == "python":
                run([sys.executable, *action_value.split()], check=True)
            else:
                raise ValueError(f"Unknown action({action_key}) for {node_name} node")


def _install_requirements(custom_nodes_dir: str | Path, node_name: str, node_details: dict) -> None:
    if "requirements" in node_details:
        for requirement in node_details["requirements"]:
            run([sys.executable, "-m", "pip", "install", requirement], check=True)
        return
    requirements = Path(custom_nodes_dir).joinpath(node_name, "requirements.txt")
    if requirements.exists() is True:
        LOGGER.info("Installing `%s` requirements", node_name)
        run([sys.executable, "-m", "pip", "install", "-r", requirements], check=True)


def _run_install_script(custom_nodes_dir: str | Path, node_name: str) -> None:
    node_install_script = Path(custom_nodes_dir).joinpath(node_name, "install.py")
    if node_install_script.exists() is True:
        LOGGER.info("Running `%s` install script", node_name)
        run([sys.executable, node_install_script], check=True)


def install_wheel(url: str, file_name: str):
    LOGGER.info("Installing `%s`", url)
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, file_name)
    with (
        open(temp_file_path, "wb") as temp_file,
        httpx.stream("GET", url, follow_redirects=True, timeout=10.0) as response,
    ):
        response.raise_for_status()
        for chunk in response.iter_bytes():
            temp_file.write(chunk)
    try:
        run([sys.executable, "-m", "pip", "install", temp_file_path], check=True)
    finally:
        os.remove(temp_file_path)
