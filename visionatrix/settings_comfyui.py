import logging
from datetime import datetime
from pathlib import Path

from . import comfyui_wrapper
from .pydantic_models import ComfyUIFolderPath, ComfyUIFolderPaths

LOGGER = logging.getLogger("visionatrix")


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
