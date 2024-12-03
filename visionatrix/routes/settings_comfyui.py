import json
from json import loads
from zlib import crc32

from fastapi import APIRouter, Body, HTTPException, Request, status

from .. import comfyui_wrapper, settings_comfyui
from ..db_queries import get_global_setting, set_global_setting
from ..pydantic_models import ComfyUIFolderPathDefinition, ComfyUIFolderPaths
from .helpers import require_admin

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

    return settings_comfyui.compute_folder_paths(comfyui_folders)


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

    try:
        comfyui_folders = settings_comfyui.add_folder_path(body)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None

    raw_data = json.dumps([i.model_dump(mode="json") for i in comfyui_folders])
    raw_data_crc32 = crc32(raw_data.encode("utf-8"))
    comfyui_wrapper.COMFYUI_FOLDERS_SETTING_CRC32 = raw_data_crc32
    set_global_setting("comfyui_folders", raw_data, sensitive=True, crc32=raw_data_crc32)
    return settings_comfyui.compute_folder_paths(comfyui_folders)


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

    try:
        comfyui_folders = settings_comfyui.remove_folder_path(folder_key, path)
    except ValueError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            str(e),
        ) from None

    raw_data = json.dumps([i.model_dump(mode="json") for i in comfyui_folders])
    raw_data_crc32 = crc32(raw_data.encode("utf-8"))
    comfyui_wrapper.COMFYUI_FOLDERS_SETTING_CRC32 = raw_data_crc32
    set_global_setting("comfyui_folders", raw_data, sensitive=True, crc32=raw_data_crc32)
    return settings_comfyui.compute_folder_paths(comfyui_folders)


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

    comfyui_folders = settings_comfyui.autoconfigure_model_folders(models_dir)

    # Update the global setting once with all folder paths
    raw_data = json.dumps([i.model_dump(mode="json") for i in comfyui_folders])
    raw_data_crc32 = crc32(raw_data.encode("utf-8"))
    comfyui_wrapper.COMFYUI_FOLDERS_SETTING_CRC32 = raw_data_crc32
    set_global_setting("comfyui_folders", raw_data, sensitive=True, crc32=raw_data_crc32)
    return settings_comfyui.compute_folder_paths(comfyui_folders)
