from fastapi import APIRouter, Request, status

from .. import settings_comfyui
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
