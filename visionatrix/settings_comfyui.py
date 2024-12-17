import logging
from datetime import datetime
from json import loads
from pathlib import Path

from . import comfyui_wrapper, options
from .db_queries import get_global_setting
from .pydantic_models import (
    ComfyUIFolderPath,
    ComfyUIFolderPathDefinition,
    ComfyUIFolderPaths,
)

LOGGER = logging.getLogger("visionatrix")


def add_folder_path(path_to_add: ComfyUIFolderPathDefinition) -> list[ComfyUIFolderPathDefinition]:
    comfyui_folders: list[ComfyUIFolderPathDefinition] = []
    if comfyui_folders_setting := get_global_setting("comfyui_folders", True):
        comfyui_folders = [ComfyUIFolderPathDefinition.model_validate(i) for i in loads(comfyui_folders_setting)]

    absolute_new_path = path_to_add.path
    if not Path(absolute_new_path).is_absolute():
        absolute_new_path = Path(options.COMFYUI_DIR).joinpath(path_to_add.path).resolve()

    for custom_folder in comfyui_folders:
        custom_folder_path = Path(custom_folder.path)
        if not custom_folder_path.is_absolute():
            custom_folder_path = Path(options.COMFYUI_DIR).joinpath(custom_folder.path).resolve()
        if path_to_add.folder_key == custom_folder.folder_key and absolute_new_path == custom_folder_path:
            raise ValueError(
                f"The folder path '{path_to_add.path}' already exists under the key '{path_to_add.folder_key}'.",
            )

    comfyui_wrapper.add_model_folder_path(path_to_add.folder_key, str(absolute_new_path), path_to_add.is_default)
    comfyui_folders.append(path_to_add)
    return comfyui_folders


def remove_folder_path(folder_key: str, path: str) -> list[ComfyUIFolderPathDefinition]:
    comfyui_folders: list[ComfyUIFolderPathDefinition] = []
    if comfyui_folders_setting := get_global_setting("comfyui_folders", True):
        comfyui_folders = [ComfyUIFolderPathDefinition.model_validate(i) for i in loads(comfyui_folders_setting)]

    absolute_path = Path(path)
    if not absolute_path.is_absolute():
        absolute_path = Path(options.COMFYUI_DIR).joinpath(path).resolve()

    updated_folders = []
    folder_found = False
    for custom_folder in comfyui_folders:
        custom_folder_path = Path(custom_folder.path)
        if not custom_folder_path.is_absolute():
            custom_folder_path = Path(options.COMFYUI_DIR).joinpath(custom_folder.path).resolve()
        if custom_folder.folder_key == folder_key and custom_folder_path == absolute_path:
            folder_found = True
        else:
            updated_folders.append(custom_folder)

    if not folder_found:
        raise ValueError(f"The folder path '{path}' under the key '{folder_key}' was not found.")

    folder_names_and_paths = comfyui_wrapper.get_folder_names_and_paths()
    if folder_key in folder_names_and_paths:
        folder_paths, _ = folder_names_and_paths[folder_key]
        try:
            folder_paths.remove(str(absolute_path))
            LOGGER.info("Removed path '%s' from ComfyUI key '%s'.", absolute_path, folder_key)
        except ValueError:
            LOGGER.error("Path '%s' not found in ComfyUI key '%s'.", absolute_path, folder_key)
    return updated_folders


def autoconfigure_model_folders(models_dir: str) -> list[ComfyUIFolderPathDefinition]:
    paths_to_preconfigure = {
        "checkpoints": "checkpoints",
        "text_encoders": "text_encoders",
        "clip_vision": "clip_vision",
        "controlnet": "controlnet",
        "diffusion_models": "diffusion_models",
        "diffusers": "diffusers",
        "ipadapter": "ipadapter",
        "instantid": "instantid",
        "loras": ["loras", "photomaker"],
        "photomaker": "photomaker",
        "sams": "sams",
        "style_models": "style_models",
        "ultralytics": "ultralytics",
        "ultralytics_bbox": "ultralytics/bbox",
        "ultralytics_segm": "ultralytics/segm",
        "unet": "unet",
        "upscale_models": "upscale_models",
        "vae": "vae",
        "vae_approx": "vae_approx",
        "pulid": "pulid",
    }

    comfyui_folders = []
    for folder_key, subpaths in paths_to_preconfigure.items():
        if isinstance(subpaths, str):
            subpaths = [subpaths]
        for subpath in subpaths:
            path = str(Path(models_dir).joinpath(subpath))
            folder_def = ComfyUIFolderPathDefinition(
                folder_key=folder_key,
                path=path,
                is_default=True,
            )

            absolute_new_path = folder_def.path
            if not Path(absolute_new_path).is_absolute():
                absolute_new_path = Path(options.COMFYUI_DIR).joinpath(folder_def.path).resolve()

            comfyui_wrapper.add_model_folder_path(folder_def.folder_key, str(absolute_new_path), folder_def.is_default)
            comfyui_folders.append(folder_def)

    return comfyui_folders


def compute_folder_paths(comfyui_folders: list[ComfyUIFolderPathDefinition]) -> ComfyUIFolderPaths:
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

            readonly = True
            is_default = False
            for custom_folder in comfyui_folders:
                custom_folder_path = Path(custom_folder.path)
                if not custom_folder_path.is_absolute():
                    custom_folder_path = Path(options.COMFYUI_DIR).joinpath(custom_folder.path).resolve()
                if key == custom_folder.folder_key and folder_path == custom_folder_path:
                    readonly = False
                    is_default = custom_folder.is_default
                    break

            folder_data[key].append(
                ComfyUIFolderPath(
                    readonly=readonly,
                    full_path=str(folder_path),
                    is_default=is_default,
                    create_time=create_time,
                    total_size=total_size,
                )
            )
    return ComfyUIFolderPaths(folders=folder_data)
