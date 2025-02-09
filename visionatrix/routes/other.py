import logging
import os
import signal
import time

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query,
    Request,
    Response,
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


@ROUTER.api_route(
    "/proxy",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    response_class=Response,
    include_in_schema=False,
)
async def universal_proxy(
    request: Request,
    target: str = Query(..., description="The fully qualified remote URL to which the request should be proxied"),
):
    """
    Universal proxy endpoint that relays a request to the specified remote URL.

    1. The request path is always /other/proxy.
    2. You must specify the remote URL via the `target` query parameter, e.g.:
       GET /other/proxy?target=https://civitai.com/api/v1/models

    Request Details:
    - Method: Determined by client's HTTP method (GET, POST, etc.).
    - Headers: Forwarded from client request except for certain hop-by-hop or irrelevant headers.
    - Body: If present (e.g. in POST/PUT), forwarded as-is.

    Response:
    - Status code: Same as remote server's response.
    - Headers: Only critical ones are returned (Content-Type, etc.).
    - Body: Remote server's response body is relayed back to the client.

    Note: If you need to limit which domains can be accessed, add a domain check for `target`.
    """

    # 1. Capture request method and body
    method = request.method
    body = b""
    if method not in ("GET", "HEAD"):
        body = await request.body()

    # 2. Prepare headers for forwarding (filter out hop-by-hop headers or ones set by Starlette)
    excluded_headers = {"host", "content-length", "transfer-encoding", "connection", "accept-encoding"}
    forward_headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}

    # 3. Make the request to the remote server
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:  # noqa
        try:
            remote_response = await client.request(
                method=method,
                url=target,
                headers=forward_headers,
                content=body,
            )
        except httpx.RequestError as exc:
            LOGGER.error("Proxy request to %s failed: %s", target, exc)
            return Response(
                content=f"Request to remote server failed: {exc}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

    # 4. Build the response with content and matching status code
    #    (If you need to preserve additional headers, add them here carefully.)
    content_type = remote_response.headers.get("content-type", "application/octet-stream")
    return Response(
        content=remote_response.content,
        status_code=remote_response.status_code,
        media_type=content_type,
    )
