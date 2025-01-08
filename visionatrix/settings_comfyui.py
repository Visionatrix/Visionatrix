import logging
from datetime import datetime
from pathlib import Path

from . import comfyui_wrapper
from .pydantic_models import ComfyUIFolderPath, ComfyUIFolderPaths

LOGGER = logging.getLogger("visionatrix")


def remove_folder_path(folder_key: str, full_folder_path: str) -> bool:
    folder_names_and_paths = comfyui_wrapper.get_folder_names_and_paths()
    if folder_key not in folder_names_and_paths:
        LOGGER.error("ComfyUI folder_key '%s' not found.", folder_key)
        return False
    folder_paths, _ = folder_names_and_paths[folder_key]
    try:
        folder_paths.remove(full_folder_path)
        LOGGER.info("Removed path '%s' from ComfyUI folder_key '%s'.", full_folder_path, folder_key)
        return True
    except ValueError:
        LOGGER.error("Path '%s' not found in ComfyUI folder_key '%s'.", full_folder_path, folder_key)
    return False


def autoconfigure_model_folders(models_dir: str) -> None:
    for comfyui_folder in comfyui_wrapper.get_autoconfigured_model_folders_from(models_dir):
        comfyui_wrapper.add_model_folder_path(comfyui_folder.folder_key, comfyui_folder.path, True)


def deconfigure_model_folders(models_dir: str) -> None:
    for old_path in comfyui_wrapper.get_autoconfigured_model_folders_from(models_dir):
        remove_folder_path(old_path.folder_key, old_path.path)


def compute_folder_paths() -> ComfyUIFolderPaths:
    folder_data = {}
    for key, (paths, _) in comfyui_wrapper.get_folder_names_and_paths().items():
        folder_data[key] = []
        for folder in paths:
            folder_path = Path(folder)
            total_size = 0
            create_time = datetime.fromtimestamp(0.0)
            if folder_path.exists() and folder_path.is_dir():
                try:
                    create_time = datetime.fromtimestamp(folder_path.stat().st_birthtime)
                except AttributeError:
                    # Fall back if `st_birthtime` is not available (e.g., on some Linux filesystems)
                    create_time = datetime.fromtimestamp(folder_path.stat().st_ctime)

                total_size = sum(f.stat().st_size for f in folder_path.rglob("*") if f.is_file())

            folder_data[key].append(
                ComfyUIFolderPath(
                    full_path=str(folder_path),
                    create_time=create_time,
                    total_size=total_size,
                )
            )
    return ComfyUIFolderPaths(folders=folder_data)
