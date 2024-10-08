import fnmatch
import logging
import os
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, responses, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from pillow_heif import register_heif_opener
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send

from . import comfyui, database, options
from .routes import flows, other, settings, tasks, workers
from .tasks_engine import (
    background_prompt_executor,
    remove_active_task_lock,
    task_progress_callback,
)
from .tasks_engine_async import start_tasks_engine
from .user_backends import perform_auth

LOGGER = logging.getLogger("visionatrix")
EXIT_EVENT = threading.Event()


class VixAuthMiddleware:
    """Pure ASGI Vix Middleware."""

    _disable_for: list[str]

    def __init__(self, app: ASGIApp, disable_for: list[str] | None = None) -> None:
        self.app = app
        self._disable_for = [] if disable_for is None else [i.lstrip("/") for i in disable_for]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Method that will be called by Starlette for each event."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        conn = HTTPConnection(scope)
        url_path = conn.url.path.lstrip("/")
        if options.VIX_MODE == "DEFAULT":
            scope["user_info"] = database.DEFAULT_USER
        elif not fnmatch.filter(self._disable_for, url_path):
            bad_auth_response = responses.Response(
                "Not authenticated",
                status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic"},
            )
            try:
                if (userinfo := await perform_auth(scope, conn)) is None:
                    await bad_auth_response(scope, receive, send)
                    return
                scope["user_info"] = userinfo
            except HTTPException as exc:
                response = self._on_error(exc.status_code, exc.detail)
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)

    @staticmethod
    def _on_error(status_code: int = 400, content: str = "") -> responses.PlainTextResponse:
        return responses.PlainTextResponse(content, status_code=status_code)


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_heif_opener()
    logging.getLogger("uvicorn.access").setLevel(logging.getLogger().getEffectiveLevel())
    tasks.VALIDATE_PROMPT, comfy_queue = comfyui.load(task_progress_callback)
    await start_tasks_engine(comfy_queue, EXIT_EVENT)
    if options.UI_DIR:
        app.mount("/", StaticFiles(directory=options.UI_DIR, html=True), name="client")
    yield
    EXIT_EVENT.set()
    comfyui.interrupt_processing()


def custom_generate_unique_id(route: APIRoute):
    try:
        return f"{route.name}"
    except Exception:
        print(f"[ERROR]: {route.name} caused an exception", flush=True)
        raise


APP = FastAPI(lifespan=lifespan, generate_unique_id_function=custom_generate_unique_id)
API_ROUTER = APIRouter(prefix="/api")
API_ROUTER.include_router(flows.ROUTER)
API_ROUTER.include_router(settings.ROUTER)
API_ROUTER.include_router(tasks.ROUTER)
API_ROUTER.include_router(workers.ROUTER)
API_ROUTER.include_router(other.ROUTER)
APP.include_router(API_ROUTER)
APP.add_middleware(VixAuthMiddleware)
if cors_origins := os.getenv("CORS_ORIGINS", "").split(","):
    APP.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def run_vix(*args, **kwargs) -> None:
    if options.VIX_MODE == "WORKER" and options.UI_DIR:
        LOGGER.error("`WORKER` mode is incompatible with UI")
        return

    for i in ("input", "output"):
        os.makedirs(os.path.join(options.TASKS_FILES_DIR, i), exist_ok=True)

    if options.VIX_MODE != "WORKER":
        try:
            if options.VIX_MODE == "SERVER":
                os.environ.update(**options.get_server_mode_options_as_env())
                _app = "visionatrix:APP"
            else:
                _app = APP
            uvicorn.run(
                _app,
                *args,
                host=options.VIX_HOST if options.VIX_HOST else "127.0.0.1",
                port=int(options.VIX_PORT) if options.VIX_PORT else 8288,
                workers=int(options.VIX_SERVER_WORKERS),
                **kwargs,
            )
        except KeyboardInterrupt:
            print("Visionatrix is shutting down.")
    else:
        register_heif_opener()
        _, comfy_queue = comfyui.load(task_progress_callback)

        try:
            background_prompt_executor(comfy_queue, EXIT_EVENT)
        except KeyboardInterrupt:
            remove_active_task_lock()
            print("Visionatrix is shutting down.")
