import json
import logging
from datetime import datetime
from json import loads
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Request, status

from .. import options
from ..comfyui_wrapper import add_model_folder_path, get_folder_names_and_paths
from ..db_queries import get_global_setting, set_global_setting
from ..pydantic_models import (
    ComfyUIFolderPath,
    ComfyUIFolderPathDefinition,
    ComfyUIFolderPaths,
)
from .helpers import require_admin

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/settings/comfyui", tags=["settings"])


@ROUTER.get(
    "/folders",
    status_code=status.HTTP_200_OK,
)
def comfyui_get_folders_paths(request: Request) -> ComfyUIFolderPaths:
    """
    Retrieves all folder paths and their metadata from the ComfyUI folder settings.

    Requires administrative privileges.
    """
    require_admin(request)

    comfyui_folders: list[ComfyUIFolderPathDefinition] = []
    if comfyui_folders_setting := get_global_setting("comfyui_folders", True):
        comfyui_folders = [ComfyUIFolderPathDefinition.model_validate(i) for i in loads(comfyui_folders_setting)]

    return compute_folder_paths(comfyui_folders)


@ROUTER.post(
    "/folders",
    status_code=status.HTTP_201_CREATED,
)
def add_folder_path(
    request: Request,
    body: ComfyUIFolderPathDefinition = Body(...),
) -> ComfyUIFolderPaths:
    """
    Adds a new folder path with a specified priority to the ComfyUI settings.

    Requires administrative privileges.
    """
    require_admin(request)

    comfyui_folders: list[ComfyUIFolderPathDefinition] = []
    if comfyui_folders_setting := get_global_setting("comfyui_folders", True):
        comfyui_folders = [ComfyUIFolderPathDefinition.model_validate(i) for i in loads(comfyui_folders_setting)]

    for custom_folder in comfyui_folders:
        if body.folder_key == custom_folder.folder_key and body.path == custom_folder.path:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"The folder path '{body.path}' already exists under the key '{body.folder_key}'.",
            )

    body_path = body.path
    if not Path(body_path).is_absolute():
        body_path = str(Path(options.COMFYUI_DIR).joinpath(body.path).resolve())
    add_model_folder_path(body.folder_key, body_path, body.is_default)

    comfyui_folders.append(body)
    set_global_setting(
        "comfyui_folders", json.dumps([i.model_dump(mode="json") for i in comfyui_folders]), sensitive=True
    )
    return compute_folder_paths(comfyui_folders)


@ROUTER.delete(
    "/folders",
    status_code=status.HTTP_200_OK,
)
def remove_folder_path(
    request: Request,
    folder_key: str = Body(..., description="The folder key (e.g., 'checkpoints', 'vae')."),
    path: str = Body(..., description="The full or relative filesystem path of the folder to remove."),
) -> ComfyUIFolderPaths:
    """
    Removes a folder path from the ComfyUI settings.

    Requires administrative privileges.
    """
    require_admin(request)

    comfyui_folders: list[ComfyUIFolderPathDefinition] = []
    if comfyui_folders_setting := get_global_setting("comfyui_folders", True):
        comfyui_folders = [ComfyUIFolderPathDefinition.model_validate(i) for i in loads(comfyui_folders_setting)]

    absolute_path = Path(path)
    if not absolute_path.is_absolute():
        absolute_path = Path(options.COMFYUI_DIR).joinpath(path).resolve()

    updated_folders = []
    folder_found = False
    for custom_folder in comfyui_folders:
        if custom_folder.folder_key == folder_key and custom_folder.path == str(absolute_path):
            folder_found = True
        else:
            updated_folders.append(custom_folder)

    if not folder_found:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"The folder path '{path}' under the key '{folder_key}' was not found.",
        )

    folder_names_and_paths = get_folder_names_and_paths()
    if folder_key in folder_names_and_paths:
        folder_paths, _ = folder_names_and_paths[folder_key]
        try:
            folder_paths.remove(str(absolute_path))
            LOGGER.info("Removed path '%s' from ComfyUI key '%s'.", absolute_path, folder_key)
        except ValueError:
            LOGGER.error("Path '%s' not found in ComfyUI key '%s'.", absolute_path, folder_key)

    set_global_setting(
        "comfyui_folders", json.dumps([i.model_dump(mode="json") for i in updated_folders]), sensitive=True
    )
    return compute_folder_paths(updated_folders)


@ROUTER.post(
    "/folders/autoconfig",
    status_code=status.HTTP_200_OK,
)
def autoconfigure_model_folders(
    request: Request,
    models_dir: str = Body(..., embed=True, description="The default folder for models."),
) -> ComfyUIFolderPaths:
    """
    Autoconfigures model paths to the selected folder.

    Requires administrative privileges.
    """
    require_admin(request)

    if get_global_setting("comfyui_folders", True):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "ComfyUI folder settings are not empty.",
        )

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
        "ultralytics": "ultralytics",
        "unet": "unet",
        "upscale_models": "upscale_models",
        "vae": "vae",
        "vae_approx": "vae_approx",
        "pulid": "pulid",
    }

    for folder_key, subpaths in paths_to_preconfigure.items():
        if isinstance(subpaths, str):
            subpaths = [subpaths]
        for subpath in subpaths:
            add_folder_path(
                request,
                ComfyUIFolderPathDefinition(
                    folder_key=folder_key,
                    path=str(Path(models_dir).joinpath(subpath)),
                    is_default=True,
                ),
            )
    return comfyui_get_folders_paths(request)


def compute_folder_paths(comfyui_folders: list[ComfyUIFolderPathDefinition]) -> ComfyUIFolderPaths:
    folder_data = {}
    for key, (paths, _) in get_folder_names_and_paths().items():
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
