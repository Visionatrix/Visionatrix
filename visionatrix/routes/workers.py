import logging

from fastapi import APIRouter, Body, HTTPException, Query, Request, responses, status

from .. import options
from ..db_queries import get_workers_details, set_worker_tasks_to_give
from ..db_queries_async import get_workers_details_async, set_worker_tasks_to_give_async
from ..pydantic_models import WorkerDetails

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/api")


@ROUTER.get("/workers_info")
async def workers_info(
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
    if options.VIX_MODE == "SERVER":
        r = await get_workers_details_async(user_id, last_seen_interval, worker_id)
    else:
        r = get_workers_details(user_id, last_seen_interval, worker_id)
    return r


@ROUTER.post(
    "/worker_tasks",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Worker tasks set successfully"},
        404: {
            "description": "Worker not found",
            "content": {"application/json": {"example": {"detail": "Can't find `worker_id` worker."}}},
        },
    },
)
async def worker_tasks_to_give_set(
    request: Request,
    worker_id: str = Body(..., description="ID of the worker"),
    tasks_to_give: list[str] = Body(..., description="List of tasks the worker can handle"),
):
    """
    Sets the tasks that a worker can work on. An empty list indicates that all tasks are allowed.
    The administrator can set `tasks_to_give` for all workers, users only for their own.
    """
    user_id = None if request.scope["user_info"].is_admin else request.scope["user_info"].user_id
    if options.VIX_MODE == "SERVER":
        r = await set_worker_tasks_to_give_async(user_id, worker_id, tasks_to_give)
    else:
        r = set_worker_tasks_to_give(user_id, worker_id, tasks_to_give)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Can't find `{worker_id}` worker.")
