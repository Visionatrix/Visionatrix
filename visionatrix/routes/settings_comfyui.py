from fastapi import APIRouter, Body, Request, status

from .. import comfyui_wrapper, settings_comfyui
from ..db_queries import set_global_setting
from ..pydantic_models import ComfyUIFolderPaths
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
    return settings_comfyui.compute_folder_paths()


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

    if models_dir != comfyui_wrapper.COMFYUI_MODELS_FOLDER:
        if comfyui_wrapper.COMFYUI_MODELS_FOLDER:
            settings_comfyui.deconfigure_model_folders(comfyui_wrapper.COMFYUI_MODELS_FOLDER)
        comfyui_wrapper.COMFYUI_MODELS_FOLDER = models_dir
        settings_comfyui.autoconfigure_model_folders(models_dir)
        set_global_setting("comfyui_models_folder", models_dir, True)

    return settings_comfyui.compute_folder_paths()
