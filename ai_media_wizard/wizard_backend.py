import contextlib
import json
import logging
import os
import signal
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

import httpx

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
from .tasks import (
    clear_unfinished_task,
    clear_unfinished_tasks,
    create_new_task,
    get_task,
    get_tasks,
    load_tasks,
    remove_task,
    save_tasks,
    track_task_progress,
)

try:
    import fastapi
    import fastapi.middleware.cors
    import fastapi.staticfiles
    import uvicorn
except ImportError as ex:
    from ._deffered_error import DeferredError

    uvicorn = fastapi = DeferredError(ex)


LOGGER = logging.getLogger("ai_media_wizard")
COMFY_PROCESS: subprocess.Popen[bytes] | None = None
FLOW_INSTALL_STATUS = {}  # {flow_name: {progress: float, error: ""}}


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
            load_tasks()
        yield
        stop_comfy()
        if ui_dir:
            save_tasks()

    app = fastapi.FastAPI(lifespan=lifespan)
    if cors_origins := os.getenv("CORS_ORIGINS", "").split(","):
        app.add_middleware(
            fastapi.middleware.cors.CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

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
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.post("/task")
    def task_run(
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

        task_id, task_details = create_new_task(name, input_params_list, backend_dir)
        try:
            flow_comfy = prepare_flow_comfy(
                flow, flow_comfy, input_params_list, in_files, task_id, task_details, backend_dir
            )
        except RuntimeError as e:
            remove_task(task_id, "")
            raise fastapi.HTTPException(status_code=400, detail=str(e)) from None

        connection = open_comfy_websocket(str(task_id))
        r = execute_flow_comfy(flow_comfy, str(task_id))
        b_tasks.add_task(
            track_task_progress,
            connection,
            r["prompt_id"],
            task_id,
            task_details,
            len(list(flow_comfy.keys())),
            backend_dir,
        )
        return fastapi.responses.JSONResponse(content={"task_id": str(task_id)})

    @app.get("/tasks-progress")
    async def tasks_progress():
        return fastapi.responses.JSONResponse(content=get_tasks())

    @app.get("/task-progress")
    async def task_progress(task_id: str):
        if (r := get_task(int(task_id))) is None:
            raise fastapi.HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
        return fastapi.responses.JSONResponse(content=r)

    @app.delete("/task")
    async def task_remove(task_id: str):
        remove_task(int(task_id), backend_dir)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.get("/task-results")
    async def task_results(task_id: str, node_id: int):
        result_prefix = f"{task_id}_{node_id}_"
        output_directory = os.path.join(backend_dir, "output")
        for filename in os.listdir(output_directory):
            if filename.startswith(result_prefix):
                return fastapi.responses.FileResponse(os.path.join(output_directory, filename))
        raise fastapi.HTTPException(status_code=404, detail=f"Missing result for task={task_id} and node={node_id}.")

    @app.delete("/tasks-queue")
    async def tasks_queue_clear(b_tasks: fastapi.BackgroundTasks):
        async def __tasks_queue_clear():
            await httpx.AsyncClient().post(url=f"http://{options.get_comfy_address()}/queue", json={"clear": True})
            await httpx.AsyncClient().post(url=f"http://{options.get_comfy_address()}/interrupt")
            clear_unfinished_tasks()

        b_tasks.add_task(__tasks_queue_clear)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.delete("/task-queue")
    async def task_queue_clear(task_id: int):
        # await httpx.AsyncClient().post(url=f"http://{options.get_comfy_address()}/queue", json={"delete": []})
        return fastapi.responses.JSONResponse(content={"error": clear_unfinished_task(task_id)})

    @app.post("/task-interrupt")
    async def task_interrupt(b_tasks: fastapi.BackgroundTasks):
        async def __interrupt_task():
            await httpx.AsyncClient().post(url=f"http://{options.get_comfy_address()}/interrupt")

        b_tasks.add_task(__interrupt_task)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.post("/backend-restart")
    def backend_restart():
        run_comfy_backend(backend_dir)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.post("/shutdown")
    def shutdown(b_tasks: fastapi.BackgroundTasks):
        def __shutdown_wizard():
            time.sleep(1.0)
            os.kill(os.getpid(), signal.SIGINT)

        stop_comfy()
        if ui_dir:
            save_tasks()
        b_tasks.add_task(__shutdown_wizard)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.get("/system_stats")
    async def system_stats():
        return fastapi.responses.JSONResponse(
            content=json.loads(
                (await httpx.AsyncClient().get(url=f"http://{options.get_comfy_address()}/system_stats")).content
            )
        )

    uvicorn.run(app, *args, host=wizard_host, port=wizard_port, **kwargs)


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
    run_cmd = [
        "python",
        os.path.join(options.get_backend_dir(backend_dir), "main.py"),
        "--port",
        str(options.get_comfy_port()),
    ]
    if need_directml_flag():
        run_cmd += ["--directml"]
    stdout = None if LOGGER.getEffectiveLevel == logging.DEBUG or options.COMFY_DEBUG != "0" else subprocess.DEVNULL
    COMFY_PROCESS = subprocess.Popen(run_cmd, stdout=stdout)  # pylint: disable=consider-using-with
    for _ in range(15):
        with contextlib.suppress(httpx.NetworkError):
            r = httpx.get(f"http://{options.get_comfy_address()}")
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
