import contextlib
import json
import logging
import os
import signal
import subprocess
import sys
import time
import uuid
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

import httpx
from websockets.sync.client import ClientConnection

from . import options
from .flows import (
    execute_flow_comfy,
    get_available_flows,
    get_installed_flow,
    get_installed_flows,
    get_not_installed_flows,
    install_custom_flow,
    open_comfy_websocket,
    prepare_flow_comfy,
    uninstall_flow,
)

try:
    import fastapi
    import fastapi.staticfiles
    import uvicorn
except ImportError as ex:
    from ._deffered_error import DeferredError

    uvicorn = fastapi = DeferredError(ex)


LOGGER = logging.getLogger("ai_media_wizard")
COMFY_PROCESS: subprocess.Popen[bytes] | None = None
FLOW_INSTALL_STATUS = {}  # {flow_name: {progress: float, error: ""}}
TASKS_PROGRESS = {}  # task_id: {request_id: str, progress: 0.0-100.0, error: "", flow: {}, flow_comfy: {}}


def wizard_backend(
    *args,
    backend_dir: str,
    flows_dir: str,
    models_dir: str,
    wizard_host: str,
    wizard_port: str,
    **kwargs,
):
    flows_dir = options.get_flows_dir(flows_dir)
    models_dir = options.get_models_dir(models_dir)
    ui_dir = kwargs.pop("ui_dir", "")
    wizard_host = options.get_wizard_host(wizard_host)
    wizard_port = options.get_wizard_port(wizard_port)

    @asynccontextmanager
    async def lifespan(_app: fastapi.FastAPI):
        if ui_dir:
            try:
                _app.mount("/", fastapi.staticfiles.StaticFiles(directory=ui_dir, html=True), name="client")
            except RuntimeError:
                stop_comfy()
                raise
        yield
        stop_comfy()

    app = fastapi.FastAPI(lifespan=lifespan)

    @app.get("/flows-installed")
    async def flows_installed():
        return fastapi.responses.JSONResponse(content=get_installed_flows(flows_dir))

    @app.get("/flows-available")
    async def flows_available():
        return fastapi.responses.JSONResponse(content=get_not_installed_flows(flows_dir))

    @app.put("/flow")
    def flow_install(b_tasks: fastapi.BackgroundTasks, name: str):
        flows, flows_comfy = get_available_flows()
        for i, flow in enumerate(flows):
            if flow["name"] == name:
                FLOW_INSTALL_STATUS[name] = {"progress": 0.0, "error": ""}
                b_tasks.add_task(
                    install_custom_flow,
                    flows_dir,
                    flow,
                    flows_comfy[i],
                    models_dir,
                    __progress_install_callback,
                )
                return fastapi.responses.JSONResponse(content={"error": ""})
        return fastapi.responses.JSONResponse(content={"error": f"Can't find `{name}` flow."})

    @app.get("/flow-progress-install")
    def flow_progress_install():
        return fastapi.responses.JSONResponse(content=FLOW_INSTALL_STATUS)

    @app.delete("/flow")
    async def flow_delete(name: str):
        uninstall_flow(flows_dir, name)
        return fastapi.responses.JSONResponse(content=[])

    @app.post("/flow")
    def flow_run(
        b_tasks: fastapi.BackgroundTasks,
        name: str = fastapi.Form(),
        input_params: str = fastapi.Form(None),
        files: list[fastapi.UploadFile] = None,  # noqa
    ):
        in_files = [i.file for i in files] if files else []
        try:
            input_params_list = json.loads(input_params) if input_params else []
        except json.JSONDecodeError:
            raise fastapi.HTTPException(status_code=400, detail="Invalid JSON format for params") from None

        flow_comfy = {}
        flow = get_installed_flow(flows_dir, name, flow_comfy)
        if not flow:
            raise fastapi.HTTPException(status_code=404, detail=f"Flow `{name}` is not installed.") from None

        request_id = str(uuid.uuid4())
        try:
            flow_comfy = prepare_flow_comfy(flow, flow_comfy, input_params_list, in_files, request_id, backend_dir)
        except RuntimeError as e:
            raise fastapi.HTTPException(status_code=400, detail=str(e)) from None

        connection = open_comfy_websocket(request_id)
        r = execute_flow_comfy(flow_comfy, request_id)
        task_details = {"request_id": request_id, "progress": 0, "error": "", "flow": flow, "flow_comfy": flow_comfy}
        TASKS_PROGRESS[r["prompt_id"]] = task_details
        b_tasks.add_task(__track_task_progress, connection, r["prompt_id"], task_details)
        return fastapi.responses.JSONResponse(content={"client_id": request_id, "task_id": r["prompt_id"]})

    @app.get("/flows-progress")
    async def flows_progress():
        return fastapi.responses.JSONResponse(content=TASKS_PROGRESS)

    @app.get("/flow-progress")
    async def flow_progress(task_id: str):
        r = TASKS_PROGRESS.get(task_id, None)
        if r is None:
            raise fastapi.HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
        return fastapi.responses.JSONResponse(content=r)

    @app.get("/flow-results")
    async def flow_results(task_id: str, node_id: int):
        r = httpx.get(f"http://127.0.0.1:{options.COMFY_PORT}/history/{task_id}")
        if r.status_code != 200:
            raise fastapi.HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
        result = json.loads(r.text)
        if task_id not in result:
            raise fastapi.HTTPException(status_code=404, detail=f"Task `{task_id}` was not found in history.")
        result_output = result[task_id]["outputs"]
        if str(node_id) not in result_output:
            raise fastapi.HTTPException(status_code=404, detail=f"Node `{node_id}` was not found in results.")
        result_node = result_output[str(node_id)]
        if "images" in result_node:
            result_image = result_node["images"][0]
            result_path = os.path.join(backend_dir, "output", result_image["subfolder"], result_image["filename"])
            return fastapi.responses.FileResponse(result_path)
        raise fastapi.HTTPException(status_code=404, detail="These node types are not currently supported.")

    @app.post("/backend-restart")
    def backend_restart():
        run_comfy_backend(backend_dir)
        return fastapi.responses.JSONResponse(content=[])

    def __shutdown_wizard():
        time.sleep(1.0)
        os.kill(os.getpid(), signal.SIGINT)

    @app.post("/shutdown")
    def shutdown(b_tasks: fastapi.BackgroundTasks):
        stop_comfy()
        b_tasks.add_task(__shutdown_wizard)
        return fastapi.responses.JSONResponse(content={"error": ""})

    uvicorn.run(app, *args, host=wizard_host, port=wizard_port, **kwargs)


def __track_task_progress(connection: ClientConnection, task_id: str, task_details: dict) -> None:
    nodes_to_execute = list(task_details["flow_comfy"].keys())
    node_percent = 100 / len(nodes_to_execute)
    current_node = ""
    while True:
        out = connection.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message["type"] == "executing":
                data = message["data"]
                if data["node"] is None and data["prompt_id"] == task_id:
                    task_details["progress"] = 100
                    break
                if data["node"] is not None and data["prompt_id"] == task_id:
                    if not current_node:
                        current_node = data["node"]
                    if current_node != data["node"]:
                        task_details["progress"] += node_percent
                        current_node = data["node"]
            elif message["type"] == "progress":
                data = message["data"]
                if "max" in data and "value" in data:
                    current_node = ""
                    task_details["progress"] += node_percent / int(data["max"])
        else:
            continue


def run_backend(
    *args,
    backend_dir="",
    flows_dir="",
    models_dir="",
    wizard_host="",
    wizard_port="",
    **kwargs,
) -> None:
    """Starts ComfyUI and AI-Media-Wizard.

    ..note:: If you use AI-Media-Wizard as a Python library you should use ``run_comfy_backend`` instead of this.
    """

    run_comfy_backend(backend_dir)
    wizard_backend(
        *args,
        backend_dir=options.get_backend_dir(backend_dir),
        flows_dir=flows_dir,
        models_dir=models_dir,
        wizard_host=wizard_host,
        wizard_port=wizard_port,
        **kwargs,
    )


def run_comfy_backend(backend_dir="") -> None:
    """Starts ComfyUI in a background."""
    global COMFY_PROCESS  # pylint: disable=global-statement

    stop_comfy()
    COMFY_PROCESS = None
    comfy_port = options.get_comfy_port()
    run_cmd = [
        "python",
        os.path.join(options.get_backend_dir(backend_dir), "main.py"),
        "--port",
        str(comfy_port),
    ]
    if need_directml_flag():
        run_cmd += ["--directml"]
    stdout = None if LOGGER.getEffectiveLevel == logging.DEBUG or options.COMFY_DEBUG != "0" else subprocess.DEVNULL
    COMFY_PROCESS = subprocess.Popen(run_cmd, stdout=stdout)  # pylint: disable=consider-using-with
    for _ in range(15):
        with contextlib.suppress(httpx.NetworkError):
            r = httpx.get(f"http://127.0.0.1:{comfy_port}")
            if r.status_code == 200:
                return
        time.sleep(0.5)
    stop_comfy()
    raise RuntimeError("Error connecting to ComfyUI")


def stop_comfy() -> None:
    if COMFY_PROCESS is not None:
        with contextlib.suppress(BaseException):
            COMFY_PROCESS.kill()


def need_directml_flag() -> bool:
    if sys.platform.lower() != "win32":
        return False

    try:
        version("torch-directml")
        LOGGER.info("DirectML package is present.")
        return True
    except PackageNotFoundError:
        LOGGER.info("No DirectML package found.")
        return False


def __progress_install_callback(name: str, progress: float, error: str) -> None:
    FLOW_INSTALL_STATUS[name] = {"progress": progress, "error": error}
