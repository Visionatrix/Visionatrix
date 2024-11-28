import logging
import os
import signal
import time

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Request,
    responses,
    status,
)

from .. import comfyui_wrapper, options
from ..prompt_translation import (
    translate_prompt_with_gemini,
    translate_prompt_with_ollama,
)
from ..pydantic_models import TranslatePromptRequest, TranslatePromptResponse, UserInfo
from .helpers import require_admin
from .settings import get_setting

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/other", tags=["other"])


@ROUTER.post(
    "/interrupt-engine",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Engine interrupt initiated successfully"},
        401: {
            "description": "Unauthorized - Admin privilege required",
            "content": {"application/json": {"example": {"detail": "Admin privilege required"}}},
        },
    },
)
async def interrupt_engine(request: Request, b_tasks: BackgroundTasks):
    """
    Interrupts the currently executing task. This is primarily an internal function and should be used
    cautiously. For standard task management, prefer using the `task_queue_clear` or `tasks_queue_clear`
    endpoints. Requires administrative privileges to execute.
    """

    def __interrupt_task():
        comfyui_wrapper.interrupt_processing()

    require_admin(request)
    if options.VIX_MODE != "SERVER":
        b_tasks.add_task(__interrupt_task)


@ROUTER.post(
    "/shutdown-server",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Server shutdown initiated successfully"},
        401: {
            "description": "Unauthorized - Admin privilege required",
            "content": {"application/json": {"example": {"detail": "Admin privilege required"}}},
        },
    },
)
async def shutdown_server(request: Request, b_tasks: BackgroundTasks):
    """
    Shuts down the current instance of Vix. This endpoint queues a task to terminate the server process
    after a short delay, ensuring any final operations can complete. Access is restricted to administrators only.
    """

    def __shutdown_vix():
        time.sleep(1.0)
        os.kill(os.getpid(), signal.SIGINT)

    require_admin(request)
    b_tasks.add_task(__shutdown_vix)


@ROUTER.get("/whoami")
async def whoami(request: Request) -> UserInfo:
    """Returns information about the currently authenticated user."""
    return request.scope["user_info"]


@ROUTER.post(
    "/translate-prompt",
    responses={
        200: {
            "description": "Translation successful",
            "content": {
                "application/json": {
                    "example": {"prompt": "Dornröschen", "result": "Sleeping Beauty", "done_reason": "stop"}
                }
            },
        },
        500: {
            "description": "Translation service error",
            "content": {"application/json": {"example": {"detail": "Translation service error"}}},
        },
    },
)
def translate_prompt(request: Request, data: TranslatePromptRequest) -> TranslatePromptResponse:
    """
    Translates an image generation prompt from another language into English.

    This endpoint accepts a prompt in any language and translates it into English.
    It returns the original prompt, the translated result, and the reason the generation was completed.

    Accessible to all authenticated users.

    Raises:
        HTTPException: If there is an error during the translation process.
    """
    user_id = request.scope["user_info"].user_id
    is_admin = request.scope["user_info"].is_admin
    try:
        translations_provider = get_setting(user_id, "translations_provider", is_admin)
        if not translations_provider:
            raise HTTPException(
                status_code=status.HTTP_412_PRECONDITION_FAILED,
                detail="Translations provider not defined",
            )
        if translations_provider == "gemini":
            return translate_prompt_with_gemini(user_id, is_admin, data)
        if translations_provider == "ollama":
            return translate_prompt_with_ollama(user_id, is_admin, data)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Unknown translation provider: {translations_provider}",
        )
    except Exception as e:
        LOGGER.exception("Error during prompt translation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation service error",
        ) from e
