import json
import os
import subprocess
from contextlib import asynccontextmanager

from . import options
from .flows import (
    execute_comfy_flow,
    get_available_flows,
    get_installed_flow,
    get_installed_flows,
    install_flow,
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
        name: str = fastapi.Form(),
        input_params: str = fastapi.Form(None),
        files: list[fastapi.UploadFile] = None,  # noqa
    ):
        if files is None:
            files = []
        try:
            input_params_list = json.loads(input_params) if input_params else []
        except json.JSONDecodeError:
            return fastapi.HTTPException(status_code=400, detail="Invalid JSON format for params")

        comfy_flow = {}
        flow = get_installed_flow(flows_dir, name, comfy_flow)
        if not flow:
            return fastapi.HTTPException(status_code=404, detail=f"Flow `{name}` is not installed.")

        try:
            comfy_flow = prepare_comfy_flow(flow, comfy_flow, input_params_list, files)
        except RuntimeError as e:
            raise fastapi.HTTPException(status_code=400, detail=str(e)) from None

        # connection, client_id = open_comfy_websocket()
        client_id = "123"
        r = execute_comfy_flow(comfy_flow, client_id)
        return fastapi.responses.JSONResponse(content={"client_id": client_id, "prompt_id": r["prompt_id"]})

    @app.post("/backend-restart")
    async def backend_restart():
        run_comfy_backend(backend_dir)
        return fastapi.responses.JSONResponse(content=[])

    uvicorn.run(
        app, *args, host=options.get_wizard_host(wizard_host), port=options.get_wizard_port(wizard_port), **kwargs
    )


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
