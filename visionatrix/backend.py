import asyncio
import base64
import fnmatch
import logging
import os
import re
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, Query, responses, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from pillow_heif import register_heif_opener
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send

from . import comfyui_wrapper, custom_openapi, database, events, options, routes
from .comfyui_proxy_middleware import ComfyUIProxyMiddleware
from .federation import federation_sync_engine
from .pydantic_models import UserInfo
from .tasks_engine import remove_active_task_lock, task_progress_callback
from .tasks_engine_async import start_tasks_engine
from .user_backends import perform_auth_http, perform_auth_ws

LOGGER = logging.getLogger("visionatrix")


class VixAuthMiddleware:
    """Pure ASGI Vix Middleware."""

    _disable_for: list[str]

    def __init__(self, app: ASGIApp, disable_for: list[str] | None = None) -> None:
        self.app = app
        self._disable_for = [] if disable_for is None else [i.lstrip("/") for i in disable_for]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Method that will be called by Starlette for each event."""
        if scope["type"] == "http":
            await self._handle_http(scope, receive, send)
        elif scope["type"] == "websocket":
            await self._handle_websocket(scope, receive, send)
        else:
            await self.app(scope, receive, send)

    async def _handle_http(self, scope: Scope, receive: Receive, send: Send) -> None:
        conn = HTTPConnection(scope)
        url_path = conn.url.path.lstrip("/")
        if options.VIX_MODE == "DEFAULT":
            scope["user_info"] = database.DEFAULT_USER
        elif not fnmatch.filter(self._disable_for, url_path):
            userinfo = self._check_admin_override_auth(conn.headers)
            if userinfo:
                scope["user_info"] = userinfo
            else:
                bad_auth_response = responses.Response(
                    "Not authenticated",
                    status.HTTP_401_UNAUTHORIZED,
                    headers={"WWW-Authenticate": "Basic"},
                )
                try:
                    if (userinfo := await perform_auth_http(scope, conn)) is None:
                        await bad_auth_response(scope, receive, send)
                        return
                    scope["user_info"] = userinfo
                except HTTPException as exc:
                    response = self._on_error(exc.status_code, exc.detail)
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)

    async def _handle_websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
        url_path = scope.get("path", "").lstrip("/")
        if options.VIX_MODE == "DEFAULT":
            scope["user_info"] = database.DEFAULT_USER
        elif not fnmatch.filter(self._disable_for, url_path):
            headers_dict, cookies_dict = parse_cookies_and_headers(scope)
            userinfo = self._check_admin_override_auth(headers_dict)
            if userinfo:
                scope["user_info"] = userinfo
            else:
                try:
                    if (userinfo := await perform_auth_ws(scope, headers_dict, cookies_dict)) is None:
                        await send({"type": "websocket.close", "code": 1008})  # Policy Violation
                        return
                    scope["user_info"] = userinfo
                except HTTPException:
                    await send({"type": "websocket.close", "code": 1011})  # Internal Error
                    return

        await self.app(scope, receive, send)

    @staticmethod
    def _on_error(status_code: int = 400, content: str = "") -> responses.PlainTextResponse:
        return responses.PlainTextResponse(content, status_code=status_code)

    @staticmethod
    def _check_admin_override_auth(headers: dict[str, str] | httpx.Headers) -> UserInfo | None:
        creds = options.get_admin_override_credentials()
        if not creds:
            return None
        auth_val = headers.get("authorization", "")
        if not auth_val.startswith("Basic "):
            return None

        encoded_creds = auth_val.split(" ", 1)[1]
        decoded = base64.b64decode(encoded_creds).decode("utf-8", errors="ignore")
        if ":" not in decoded:
            return None

        user_req, pass_req = decoded.split(":", 1)
        if user_req == creds[0] and pass_req == creds[1]:
            return UserInfo(user_id=user_req, full_name=f"Admin Override {user_req}", email="", is_admin=True)
        return None


def parse_cookies_and_headers(scope: Scope) -> tuple[dict[str, str], dict[str, str]]:
    """Pull out all raw headers from a WebSocket handshake, decode them,
    and parse cookies as well. Returns (headers_dict, cookies_dict).
    """
    raw_headers = scope.get("headers", [])
    headers_dict = {}
    cookies_dict = {}
    for key_bytes, value_bytes in raw_headers:
        key = key_bytes.decode("latin-1").lower()
        value = value_bytes.decode("latin-1")
        headers_dict[key] = value
        if key == "cookie":
            cookie_pairs = value.split(";")
            for cookie_str in cookie_pairs:
                name, _, val = cookie_str.strip().partition("=")
                cookies_dict[name] = val
    return headers_dict, cookies_dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_heif_opener()
    logging.getLogger("uvicorn.access").setLevel(logging.getLogger().getEffectiveLevel())
    await database.init_database_engine()

    routes.tasks_internal.VALIDATE_PROMPT, prompt_server_args, start_all_func = await comfyui_wrapper.load(
        task_progress_callback
    )
    if options.VIX_MODE != "SERVER":
        await start_tasks_engine(prompt_server_args, events.EXIT_EVENT)

    if options.UI_DIR:
        app.mount("/comfy", StaticFiles(directory=Path(options.COMFYUI_DIR).joinpath("web"), html=False), name="comfy")
        app.mount("/", StaticFiles(directory=options.UI_DIR, html=True), name="client")

    _ = asyncio.create_task(federation_sync_engine(events.EXIT_EVENT_ASYNC))  # noqa
    _ = asyncio.create_task(start_all_func())  # noqa
    yield
    events.EXIT_EVENT.set()
    events.EXIT_EVENT_ASYNC.set()
    comfyui_wrapper.interrupt_processing()


def custom_generate_unique_id(route: APIRoute):
    try:
        return f"{route.name}"
    except Exception:
        print(f"[ERROR]: {route.name} caused an exception", flush=True)
        raise


APP = FastAPI(lifespan=lifespan, generate_unique_id_function=custom_generate_unique_id)


@APP.get("/comfy/", description="Original ComfyUI user interface")
async def custom_index():
    file_path = Path(options.COMFYUI_DIR).joinpath("web", "index.html")
    response = responses.FileResponse(file_path)
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


API_ROUTER = APIRouter(prefix="/vapi")  # if you change the prefix, also change it in custom_openapi.py
API_ROUTER.include_router(routes.flows.ROUTER)
API_ROUTER.include_router(routes.models.ROUTER)
API_ROUTER.include_router(routes.other.ROUTER)
API_ROUTER.include_router(routes.settings.ROUTER)
API_ROUTER.include_router(routes.settings_comfyui.ROUTER)
API_ROUTER.include_router(routes.tasks.ROUTER)
API_ROUTER.include_router(routes.workers.ROUTER)
API_ROUTER.include_router(routes.federation.ROUTER)
APP.include_router(API_ROUTER)
APP.add_middleware(ComfyUIProxyMiddleware, comfy_url="127.0.0.1:8188")
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

    os.makedirs(options.INPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(options.OUTPUT_DIR, "visionatrix"), exist_ok=True)

    # temporary code, until May 1 =====================
    # Pattern for non-mp4 files (underscore before extension is required)
    pattern_default = re.compile(r"^\d+_\d+(?:_\d+)?_\..+$")
    # Pattern for mp4 files (underscore before extension is optional)
    pattern_mp4 = re.compile(r"^\d+_\d+(?:_\d+)?\.mp4$", re.IGNORECASE)

    destination = os.path.join(options.OUTPUT_DIR, "visionatrix")
    copied_files = 0

    for filename in os.listdir(options.OUTPUT_DIR):
        file_path = os.path.join(options.OUTPUT_DIR, filename)
        if os.path.isfile(file_path) and (pattern_default.match(filename) or pattern_mp4.match(filename)):
            shutil.move(file_path, destination)
            copied_files += 1

    if copied_files:
        LOGGER.warning("Migration ot output files done, %s files - migrated.", copied_files)
    # =================================================

    if options.VIX_MODE != "WORKER":
        if options.VIX_MODE == "SERVER":
            os.environ.update(**options.get_server_mode_options_as_env())
            _app = "visionatrix:APP"
        else:
            _app = APP
        uvicorn.run(
            _app,
            *args,
            host=options.get_host_to_map(),
            port=options.get_port_to_map(),
            workers=int(options.VIX_SERVER_WORKERS),
            **kwargs,
        )
    else:
        register_heif_opener()
        asyncio.run(run_in_worker_mode())


async def run_in_worker_mode() -> None:
    _, prompt_server_args, _ = await comfyui_wrapper.load(task_progress_callback)
    await start_tasks_engine(prompt_server_args, events.EXIT_EVENT)
    try:
        await asyncio.Future()
    except asyncio.exceptions.CancelledError:
        print("Got signal to stop execution.")
    finally:
        events.EXIT_EVENT.set()
        events.EXIT_EVENT_ASYNC.set()
        await remove_active_task_lock()
        print("Visionatrix is shutting down.")


def generate_openapi(flows: str = "", skip_not_installed: bool = True, exclude_base: bool = False):
    return custom_openapi.generate_openapi(APP, flows, skip_not_installed, exclude_base)


APP.openapi = generate_openapi


@APP.get("/openapi/flows.json", include_in_schema=False)
async def openapi_flows_json(
    flows: str = Query("", description="Flows to include in OpenAPI specs (comma-separated list or '*')"),
    skip_not_installed: bool = Query(True, description="Skip flows that are not installed"),
):
    return custom_openapi.generate_openapi(APP, flows=flows, skip_not_installed=skip_not_installed)


@APP.get("/docs/flows", include_in_schema=False)
async def docs_flows(
    flows: str = Query("*", description="Flows to include in OpenAPI specs (comma-separated list or '*')"),
    skip_not_installed: bool = Query(True, description="Skip flows that are not installed"),
):
    query_params = []
    if flows:
        query_params.append(f"flows={flows}")
    if not skip_not_installed:
        query_params.append("skip_not_installed=false")
    query_string = "&".join(query_params)
    openapi_url = "/openapi/flows.json"
    if query_string:
        openapi_url += f"?{query_string}"
    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title="Flows Documentation",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )
