import logging

from fastapi import APIRouter, Body, HTTPException, Query, Request, responses, status

from .. import db_queries
from ..pydantic_models import WorkerDetails, WorkerSettingsRequest

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/workers", tags=["workers"])


@ROUTER.get("/info")
async def get_info(
    request: Request,
    last_seen_interval: int = Query(
        0,
        description="The time interval in seconds within which workers must have marked themselves active. "
        "If specified, only workers who have reported activity within this interval will be returned.",
    ),
    worker_id: str = Query("", description="An optional worker ID to retrieve details for a specific worker."),
) -> list[WorkerDetails]:
    """
    Fetches details about workers including their system and device information.
    This endpoint allows filtering of workers based on their last active status and can also
    retrieve information for a specific worker if a worker ID is provided.
    Useful for monitoring and managing worker resources in distributed computing environments.
    """
    user_id = None if request.scope["user_info"].is_admin else request.scope["user_info"].user_id
    return await db_queries.get_workers_details(user_id, last_seen_interval, worker_id, include_federated=True)


@ROUTER.post(
    "/settings",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Worker settings set successfully"},
        404: {
            "description": "Worker not found",
            "content": {"application/json": {"example": {"detail": "Can't find `worker_id` worker."}}},
        },
    },
)
async def set_worker_settings(request: Request, data: WorkerSettingsRequest = Body(...)):
    """
    Sets the desired worker settings that should differ from the defaults.
    The administrator can change settings for all workers, users only for their own workers.
    """
    user_id = None if request.scope["user_info"].is_admin else request.scope["user_info"].user_id
    if not await db_queries.save_worker_settings(user_id, data):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Can't find `{data.worker_id}` worker.")


@ROUTER.get(
    "/default_engine_settings",
    response_class=responses.JSONResponse,
    status_code=status.HTTP_200_OK,
)
async def default_engine_settings() -> dict[str, bool | int | str | float]:
    """Route only for remote workers. Returns default configured values for the ComfyUI engine."""
    return await db_queries.get_all_global_settings_for_task_execution()


@ROUTER.delete(
    "",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Worker(s) deleted successfully"},
        404: {
            "description": "Worker(s) not found",
            "content": {"application/json": {"example": {"detail": "No workers matched the criteria."}}},
        },
    },
)
async def delete_workers(
    request: Request,
    worker_id: list[str] = Query(
        ...,
        description=(
            "One or more worker IDs to delete. "
            "You can supply this parameter multiple times, e.g. "
            "`?worker_id=id1&worker_id=id2`"
        ),
    ),
) -> None:
    """Delete one or many workers.

    * Administrators can delete **any** workers.
    * Regular users can delete **only** their own workers.

    A **204** status is returned on success, **404** if nothing matched.
    """
    user_info = request.scope["user_info"]
    current_user_id = None if user_info.is_admin else user_info.user_id
    if not await db_queries.delete_workers(current_user_id, worker_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No workers matched the criteria.",
        )
