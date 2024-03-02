import json
import os
import subprocess
import uuid
from contextlib import asynccontextmanager

from websockets.sync.client import ClientConnection

from . import options
from .flows import (
    execute_comfy_flow,
    get_available_flows,
    get_installed_flow,
    get_installed_flows,
    install_flow,
    open_comfy_websocket,
    prepare_comfy_flow,
    uninstall_flow,
)

try:
    import fastapi
    import uvicorn
except ImportError as ex:
    from ._deffered_error import DeferredError

    uvicorn = fastapi = DeferredError(ex)


COMFY_PROCESS: subprocess.Popen[bytes] | None = None
PROGRESS_TRACKING = {}  # prompt_id: {queue_number: 0-9999, progress: 0.0-100.0, error: ""}


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

    @asynccontextmanager
    async def lifespan(_app: fastapi.FastAPI):
        yield

    app = fastapi.FastAPI(lifespan=lifespan)

    @app.get("/flows-installed")
    async def flows_installed():
        return fastapi.responses.JSONResponse(content=get_installed_flows(flows_dir))

    @app.get("/flows-available")
    async def flows_available():
        return fastapi.responses.JSONResponse(content=get_available_flows(flows_dir))

    @app.put("/flow")
    async def flow_install(name: str):
        return fastapi.responses.JSONResponse(content={"error": install_flow(flows_dir, name, models_dir)})

    @app.delete("/flow")
    async def flow_delete(name: str):
        uninstall_flow(flows_dir, name)
        return fastapi.responses.JSONResponse(content=[])

    @app.post("/flow")
    async def flow_run(
        b_tasks: fastapi.BackgroundTasks,
        name: str = fastapi.Form(),
        input_params: str = fastapi.Form(None),
        files: list[fastapi.UploadFile] = None,  # noqa
    ):
        if files is None:
            files = []
        try:
            input_params_list = json.loads(input_params) if input_params else []
        except json.JSONDecodeError:
            raise fastapi.HTTPException(status_code=400, detail="Invalid JSON format for params") from None

        comfy_flow = {}
        flow = get_installed_flow(flows_dir, name, comfy_flow)
        if not flow:
            raise fastapi.HTTPException(status_code=404, detail=f"Flow `{name}` is not installed.") from None

        try:
            comfy_flow = prepare_comfy_flow(flow, comfy_flow, input_params_list, files)
        except RuntimeError as e:
            raise fastapi.HTTPException(status_code=400, detail=str(e)) from None

        request_id = str(uuid.uuid4())
        connection = open_comfy_websocket(request_id)
        r = execute_comfy_flow(comfy_flow, request_id)
        b_tasks.add_task(__track_task_progress, connection, r["prompt_id"], comfy_flow)
        return fastapi.responses.JSONResponse(content={"client_id": request_id, "prompt_id": r["prompt_id"]})

    @app.get("/prompt-progress")
    async def prompt_progress(prompt_id: str):
        r = PROGRESS_TRACKING.get(prompt_id, None)
        if r is None:
            raise fastapi.HTTPException(status_code=404, detail=f"Prompt `{prompt_id}` was not found.")
        return fastapi.responses.JSONResponse(content=r)

    @app.post("/backend-restart")
    async def backend_restart():
        run_comfy_backend(backend_dir)
        return fastapi.responses.JSONResponse(content=[])

    uvicorn.run(
        app, *args, host=options.get_wizard_host(wizard_host), port=options.get_wizard_port(wizard_port), **kwargs
    )


def __track_task_progress(connection: ClientConnection, prompt_id: str, comfy_flow: dict) -> None:
    task = {"queue_number": -1, "progress": 0, "error": ""}
    nodes_to_execute = list(comfy_flow.keys())
    node_percent = 100 / len(nodes_to_execute)
    current_node = ""
    PROGRESS_TRACKING.update({prompt_id: task})
    while True:
        out = connection.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message["type"] == "executing":
                data = message["data"]
                if data["node"] is None and data["prompt_id"] == prompt_id:
                    task["progress"] = 100
                    break
                if data["node"] is not None and data["prompt_id"] == prompt_id:
                    if not current_node:
                        current_node = data["node"]
                    if current_node != data["node"]:
                        task["progress"] += node_percent
                        current_node = data["node"]
            elif message["type"] == "progress":
                data = message["data"]
                if "max" in data and "value" in data:
                    current_node = ""
                    task["progress"] += node_percent / int(data["max"])
            elif message["type"] == "status":
                task["queue_number"] = message["data"]["status"]["exec_info"]["queue_remaining"]
            elif message["type"] == "execution_start":
                data = message["data"]
                if data["prompt_id"] == prompt_id:
                    task["queue_number"] = 0
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
    if COMFY_PROCESS is not None:
        COMFY_PROCESS.kill()
        COMFY_PROCESS = None
    run_cmd = f"python {os.path.join(options.get_backend_dir(backend_dir), 'main.py')}".split()
    COMFY_PROCESS = subprocess.Popen(run_cmd)  # pylint: disable=consider-using-with
