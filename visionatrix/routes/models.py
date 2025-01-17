import logging

from fastapi import APIRouter, HTTPException, Request, responses, status

from .. import db_queries, orphan_models
from ..pydantic_models import OrphanModel
from .helpers import require_admin

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/models", tags=["models"])


@ROUTER.get(
    "/orphan",
    responses={
        200: {
            "description": "List of orphaned models retrieved successfully.",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "path": "models/example_model.ckpt",
                            "full_path": "/absolute/path/to/models/example_model.ckpt",
                            "size": 512.3,
                            "creation_time": 1695724800.0,
                            "res_model": None,
                            "possible_flows": [],
                        }
                    ]
                }
            },
        },
        400: {
            "description": "Ongoing installation prevents orphan model detection.",
            "content": {
                "application/json": {
                    "example": {"detail": "Cannot run orphan models detection during ongoing installations."}
                }
            },
        },
    },
)
def get_orphan_models(request: Request) -> list[OrphanModel]:
    """
    Retrieves a list of orphaned AI model files not associated with any installed flow.

    Orphaned models are files found in ComfyUI's model directories that are not required
    by installed flows. This endpoint provides metadata for each orphaned model,
    including file path, size, and potential usage in flows.

    Access to this endpoint is restricted to administrators.
    """
    require_admin(request)

    if db_queries.flows_installation_in_progress() or db_queries.models_installation_in_progress():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot run orphan models detection during ongoing installations."
        )
    return orphan_models.get_orphan_models()


@ROUTER.delete(
    "/orphan",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {
            "description": "Orphaned model successfully deleted.",
        },
        400: {
            "description": "Invalid input or ongoing installations prevent deletion.",
            "content": {
                "application/json": {
                    "example": {"detail": "Cannot delete orphan models during ongoing installations."}
                },
            },
        },
        404: {
            "description": "File not found at the specified path.",
            "content": {
                "application/json": {
                    "example": {"detail": "File not found at path: /absolute/path/to/models/example_model.ckpt"}
                }
            },
        },
        500: {
            "description": "Internal server error during deletion.",
            "content": {
                "application/json": {"example": {"detail": "Failed to delete orphan model: Unknown error occurred."}},
            },
        },
    },
)
def delete_orphan_model(request: Request, full_orphan_path: str, file_creation_time: float):
    """
    Deletes a specified orphaned model file.

    This endpoint removes an orphaned model if:
    - There are no ongoing model or flow installations.
    - The specified `full_path` and `file_creation_time` correspond to an orphaned model.

    Access to this endpoint is restricted to administrators.
    """
    require_admin(request)

    if db_queries.flows_installation_in_progress() or db_queries.models_installation_in_progress():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete orphan models during ongoing installations.")

    orphaned_models = {(orphan.full_path, orphan.creation_time) for orphan in orphan_models.get_orphan_models()}
    if (full_orphan_path, file_creation_time) not in orphaned_models:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"The specified path '{full_orphan_path}' with the provided creation time is not an orphaned model.",
        )

    try:
        orphan_models.remove_orphan_model(full_orphan_path)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"File not found at path: {full_orphan_path}") from None
    except Exception as e:
        LOGGER.exception("Error occurred while deleting orphan model '%s'.", full_orphan_path)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to delete orphan model: {e}") from None
