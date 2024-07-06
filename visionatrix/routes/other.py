import logging
import os
import signal
import time

from fastapi import APIRouter, BackgroundTasks, Request, responses, status

from .. import comfyui, options
from ..pydantic_models import UserInfo
from .helpers import require_admin

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/api")


@ROUTER.post(
    "/engine-interrupt",
    responses={
        204: {"description": "Engine interrupt initiated successfully"},
        401: {
            "description": "Unauthorized - Admin privilege required",
            "content": {"application/json": {"example": {"detail": "Admin privilege required"}}},
        },
    },
)
async def engine_interrupt(request: Request, b_tasks: BackgroundTasks):
    """
    Interrupts the currently executing task. This is primarily an internal function and should be used
    cautiously. For standard task management, prefer using the `task_queue_clear` or `tasks_queue_clear`
    endpoints. Requires administrative privileges to execute.
    """

    def __interrupt_task():
        comfyui.interrupt_processing()

    require_admin(request)
    if options.VIX_MODE != "SERVER":
        b_tasks.add_task(__interrupt_task)
    return responses.Response(status_code=status.HTTP_204_NO_CONTENT)


@ROUTER.post(
    "/shutdown",
    responses={
        204: {"description": "Server shutdown initiated successfully"},
        401: {
            "description": "Unauthorized - Admin privilege required",
            "content": {"application/json": {"example": {"detail": "Admin privilege required"}}},
        },
    },
)
async def shutdown(request: Request, b_tasks: BackgroundTasks):
    """
    Shuts down the current instance of Vix. This endpoint queues a task to terminate the server process
    after a short delay, ensuring any final operations can complete. Access is restricted to administrators only.
    """

    def __shutdown_vix():
        time.sleep(1.0)
        os.kill(os.getpid(), signal.SIGINT)

    require_admin(request)
    b_tasks.add_task(__shutdown_vix)
    return responses.Response(status_code=status.HTTP_204_NO_CONTENT)


@ROUTER.get("/whoami")
async def who_am_i(request: Request) -> UserInfo:
    """Returns information about the currently authenticated user."""
    return request.scope["user_info"]
