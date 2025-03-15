import asyncio
import importlib.metadata
import logging
import os
import stat
import sys
from pathlib import Path
from shutil import rmtree
from subprocess import CalledProcessError, check_call, run

from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import Version

from .. import _version, basic_node_list, comfyui_wrapper, options
from ..flows import get_available_flows, get_installed_flows, install_custom_flow
from .custom_nodes import install_base_custom_nodes, update_base_custom_nodes

LOGGER = logging.getLogger("visionatrix")


def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def install() -> None:
    """Deletes all Flows and performs a clean installation of ComfyUI."""
    dev_release = Version(_version.__version__).is_devrelease
    comfyui_dir = Path(options.COMFYUI_DIR)
    if comfyui_dir.exists():
        LOGGER.info("Removing existing ComfyUI directory: %s", comfyui_dir)
        rmtree(comfyui_dir, onerror=remove_readonly)
    os.makedirs(comfyui_dir)
    logging.info("Installing ComfyUI..")
    check_call(["git", "clone", "https://github.com/comfyanonymous/ComfyUI.git", comfyui_dir])
    if not dev_release:
        clone_env = os.environ.copy()
        clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
        check_call(["git", "checkout", f"tags/{basic_node_list.COMFYUI_RELEASE_TAG}"], env=clone_env, cwd=comfyui_dir)
    run(
        [sys.executable, "-m", "pip", "install", "-r", comfyui_dir.joinpath("requirements.txt")],
        check=True,
    )
    create_nodes_stuff()
    comfyui_manager_path = Path(comfyui_dir).joinpath("custom_nodes").joinpath("ComfyUI-Manager")
    logging.info("Installing ComfyUI-Manager..")
    check_call(["git", "clone", "https://github.com/ltdrdata/ComfyUI-Manager.git", comfyui_manager_path])
    if not dev_release:
        clone_env = os.environ.copy()
        clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
        check_call(
            ["git", "checkout", f"tags/{basic_node_list.COMFYUI_MANAGER_RELEASE_TAG}"],
            env=clone_env,
            cwd=comfyui_manager_path,
        )
    run(
        [sys.executable, "-m", "pip", "install", "-r", comfyui_manager_path.joinpath("requirements.txt")],
        check=True,
    )
    install_base_custom_nodes()
    # Temporary workarounds
    run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "bitsandbytes"],
        check=True,
    )
    # ======


def update() -> None:
    logging.info("Updating ComfyUI..")
    dev_release = Version(_version.__version__).is_devrelease
    comfyui_dir = Path(options.COMFYUI_DIR)
    requirements_path = os.path.join(comfyui_dir, "requirements.txt")
    old_requirements = Path(requirements_path).read_text(encoding="utf-8")
    if dev_release:
        check_call(["git", "checkout", "master"], cwd=comfyui_dir)
        try:
            check_call("git pull".split(), cwd=comfyui_dir)
        except CalledProcessError:
            logging.error("git pull for '%s' folder failed. Trying apply the `rebase` flag..", comfyui_dir)
            check_call("git pull --rebase".split(), cwd=comfyui_dir)
    else:
        check_call(["git", "fetch", "--all"], cwd=comfyui_dir)
        clone_env = os.environ.copy()
        clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
        check_call(
            ["git", "checkout", f"tags/{basic_node_list.COMFYUI_MANAGER_RELEASE_TAG}"], env=clone_env, cwd=comfyui_dir
        )
    if Path(requirements_path).read_text(encoding="utf-8") != old_requirements:
        check_call(
            [sys.executable, "-m", "pip", "install", "-r", os.path.join(comfyui_dir, "requirements.txt")],
        )
    create_nodes_stuff()
    comfyui_manager_path = Path(comfyui_dir).joinpath("custom_nodes").joinpath("ComfyUI-Manager")
    logging.info("Updating ComfyUI-Manager..")
    requirements_path = os.path.join(comfyui_manager_path, "requirements.txt")
    old_requirements = Path(requirements_path).read_text(encoding="utf-8")
    if dev_release:
        check_call(["git", "checkout", "main"], cwd=comfyui_manager_path)
        try:
            check_call("git pull".split(), cwd=comfyui_manager_path)
        except CalledProcessError:
            logging.error("git pull for '%s' folder failed. Trying apply the `rebase` flag..", comfyui_manager_path)
            check_call("git pull --rebase".split(), cwd=comfyui_manager_path)
    else:
        check_call(["git", "fetch", "--all"], cwd=comfyui_manager_path)
        clone_env = os.environ.copy()
        clone_env["GIT_CONFIG_PARAMETERS"] = "'advice.detachedHead=false'"
        check_call(
            ["git", "checkout", f"tags/{basic_node_list.COMFYUI_MANAGER_RELEASE_TAG}"],
            env=clone_env,
            cwd=comfyui_manager_path,
        )
    if Path(requirements_path).read_text(encoding="utf-8") != old_requirements:
        check_call(
            [sys.executable, "-m", "pip", "install", "-r", os.path.join(comfyui_manager_path, "requirements.txt")],
        )
    logging.info("Updating custom nodes..")
    update_base_custom_nodes()
    # Temporary workarounds
    run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "bitsandbytes"],
        check=True,
    )
    # ======
    asyncio.run(comfyui_wrapper.load(None))
    logging.info("Updating flows..")
    avail_flows_comfy = {}
    avail_flows = asyncio.run(get_available_flows(avail_flows_comfy))
    for i in asyncio.run(get_installed_flows()):
        if i in avail_flows:
            install_custom_flow(avail_flows[i], avail_flows_comfy[i])
        else:
            logging.warning("`%s` flow not found in repository, skipping update of it.", i)


def create_nodes_stuff() -> None:
    """Currently we only create `skip_download_model` file in "custom_nodes" for ComfyUI-Impact-Pack"""

    with Path(options.COMFYUI_DIR).joinpath("custom_nodes").joinpath("skip_download_model").open("a", encoding="utf-8"):
        pass


def update_pip_auto_fix_requirements() -> None:
    """
    Merges existing requirements in `pip_auto_fix.list` with the
    requirements of 'visionatrix' so that 'visionatrix' requirements
    take priority. Only writes back if changes were made.
    """
    pip_auto_fix_path = (
        Path(options.USER_DIR).joinpath("default").joinpath("ComfyUI-Manager").joinpath("pip_auto_fix.list")
    )
    pip_auto_fix_path.parent.mkdir(parents=True, exist_ok=True)
    if not pip_auto_fix_path.exists():
        pip_auto_fix_path.touch()

    existing_reqs = {}
    with pip_auto_fix_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                parsed_req = Requirement(line)
                existing_reqs[parsed_req.name.lower()] = parsed_req
            except InvalidRequirement:
                LOGGER.warning("Failed to parse requirement line from pip_auto_fix: %s", line)
                continue

    visionatrix_reqs = _get_visionatrix_requirements()

    merged_reqs = existing_reqs.copy()
    merged_reqs.update({req.name.lower(): req for req in visionatrix_reqs.values()})

    if merged_reqs != existing_reqs:
        with pip_auto_fix_path.open("w", encoding="utf-8") as f:
            for req_obj in merged_reqs.values():
                f.write(str(req_obj) + "\n")


def _get_visionatrix_requirements():
    """
    Retrieve and parse the requirements declared by the 'visionatrix' package
    from its metadata using importlib.metadata.
    """
    try:
        # The distribution name must match exactly what's in your package metadata
        # (e.g. setup.py: `name="visionatrix"` or pyproject.toml: `project.name = "visionatrix"`).
        # This returns None if no dependencies were declared.
        raw_reqs = importlib.metadata.requires("visionatrix") or []
    except importlib.metadata.PackageNotFoundError:
        LOGGER.warning("'visionatrix' distribution not found. No requirements to merge.")
        return {}

    visionatrix_reqs = {}
    for line in raw_reqs:
        # Each line is something like 'some_pkg>=1.2,<2.0' or 'other_pkg==5.6'
        # We parse them into packaging.requirements.Requirement objects
        try:
            req = Requirement(line)
            # Skip any requirement that specifies an extra (e.g. dev, pgsql, etc.)
            if req.marker is not None and "extra" in str(req.marker):
                continue
            # Skip any requirement that does not include version information.
            if not req.specifier:
                continue
            # Skip any requirement that specifies extras in its package name.
            if req.extras:
                continue
            if req.name.lower() == "python-dotenv":
                continue
            visionatrix_reqs[req.name.lower()] = req
        except Exception as exc:
            LOGGER.warning("Failed to parse requirement line '%s': %s", line, exc)
    return visionatrix_reqs
