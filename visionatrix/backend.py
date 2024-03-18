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


LOGGER = logging.getLogger("visionatrix")
COMFY_PROCESS: subprocess.Popen[bytes] | None = None
FLOW_INSTALL_STATUS = {}  # {flow_name: {progress: float, error: ""}}


def vix_backend(
    *args,
    backend_dir: str,
    flows_dir: str,
    models_dir: str,
    tasks_files_dir: str,
    vix_host: str,
    vix_port: str,
    **kwargs,
):
    flows_dir = options.get_flows_dir(flows_dir)
    models_dir = options.get_models_dir(models_dir)
    ui_dir = kwargs.pop("ui_dir", "")
    vix_host = options.get_host(vix_host)
    vix_port = options.get_port(vix_port)

    @asynccontextmanager
    async def lifespan(_app: fastapi.FastAPI):
        if ui_dir:
            try:
                _app.mount("/", fastapi.staticfiles.StaticFiles(directory=ui_dir, html=True), name="client")
            except RuntimeError:
                stop_comfy()
                raise
            load_tasks(tasks_files_dir)
        yield
        stop_comfy()
        if ui_dir:
            save_tasks(tasks_files_dir)

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
    async def flow_progress_install():
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

        task_id, task_details = create_new_task(name, input_params_list, tasks_files_dir)
        try:
            flow_comfy = prepare_flow_comfy(
                flow, flow_comfy, input_params_list, in_files, task_id, task_details, tasks_files_dir
            )
        except RuntimeError as e:
            remove_task(task_id, "")
            raise fastapi.HTTPException(status_code=400, detail=str(e)) from None

        connection = open_comfy_websocket(str(task_id))
        r = execute_flow_comfy(flow_comfy, str(task_id))
        task_details["prompt_id"] = r["prompt_id"]
        b_tasks.add_task(
            track_task_progress,
            connection,
            task_id,
            task_details,
            len(list(flow_comfy.keys())),
            tasks_files_dir,
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
        remove_task(int(task_id), tasks_files_dir)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.get("/task-results")
    async def task_results(task_id: str, node_id: int):
        result_prefix = f"{task_id}_{node_id}_"
        output_directory = os.path.join(tasks_files_dir, "output")
        for filename in os.listdir(output_directory):
            if filename.startswith(result_prefix):
                return fastapi.responses.FileResponse(os.path.join(output_directory, filename))
        raise fastapi.HTTPException(status_code=404, detail=f"Missing result for task={task_id} and node={node_id}.")

    @app.delete("/tasks-queue")
    async def tasks_queue_clear(name: str):
        tasks = get_tasks()
        delete_ids = []
        delete_keys = []
        for k, v in tasks.items():
            if not name or v["name"] == name and v["progress"] != 100.0:
                v["interrupt"] = True
                delete_ids.append(v["prompt_id"])
                delete_keys.append(k)
        await httpx.AsyncClient().post(url=f"http://{options.get_comfy_address()}/queue", json={"delete": delete_ids})
        for k in delete_keys:
            tasks.pop(k, None)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.delete("/task-queue")
    async def task_queue_clear(task_id: int):
        if not (r := get_task(task_id)):
            return fastapi.responses.JSONResponse(status_code=404, content={"error": "not found"})
        r["interrupt"] = True
        prompt_id = r["prompt_id"]
        get_tasks().pop(task_id, None)
        await httpx.AsyncClient().post(url=f"http://{options.get_comfy_address()}/queue", json={"delete": [prompt_id]})
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.post("/task-interrupt")
    async def task_interrupt(b_tasks: fastapi.BackgroundTasks):
        async def __interrupt_task():
            await httpx.AsyncClient().post(url=f"http://{options.get_comfy_address()}/interrupt")

        b_tasks.add_task(__interrupt_task)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.post("/backend-restart")
    def backend_restart():
        run_comfy_backend(backend_dir, tasks_files_dir)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.post("/shutdown")
    def shutdown(b_tasks: fastapi.BackgroundTasks):
        def __shutdown_vix():
            time.sleep(1.0)
            os.kill(os.getpid(), signal.SIGINT)

        stop_comfy()
        if ui_dir:
            save_tasks(tasks_files_dir)
        b_tasks.add_task(__shutdown_vix)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.get("/system_stats")
    async def system_stats():
        return fastapi.responses.JSONResponse(
            content=json.loads(
                (await httpx.AsyncClient().get(url=f"http://{options.get_comfy_address()}/system_stats")).content
            )
        )

    uvicorn.run(app, *args, host=vix_host, port=vix_port, **kwargs)


def run_backend(
    *args,
    backend_dir="",
    flows_dir="",
    models_dir="",
    tasks_files_dir="",
    vix_host="",
    vix_port="",
    **kwargs,
) -> None:

    backend_dir = options.get_backend_dir(backend_dir)
    tasks_files_dir = options.get_tasks_files_dir(tasks_files_dir)
    for i in ("input", "output"):
        os.makedirs(os.path.join(tasks_files_dir, i), exist_ok=True)

    run_comfy_backend(backend_dir, tasks_files_dir)
    vix_backend(
        *args,
        backend_dir=backend_dir,
        flows_dir=flows_dir,
        models_dir=models_dir,
        tasks_files_dir=tasks_files_dir,
        vix_host=vix_host,
        vix_port=vix_port,
        **kwargs,
    )


def run_comfy_backend(backend_dir: str, tasks_files_dir: str) -> None:
    """Starts ComfyUI in a background."""
    global COMFY_PROCESS  # pylint: disable=global-statement

    stop_comfy()
    COMFY_PROCESS = None
    run_cmd = [
        sys.executable,
        os.path.join(backend_dir, "main.py"),
        "--port",
        str(options.get_comfy_port()),
        "--output-directory",
        os.path.join(tasks_files_dir, "output"),
        "--input-directory",
        os.path.join(tasks_files_dir, "input"),
    ]
    if need_directml_flag():
        run_cmd += ["--directml"]
    stdout = None if LOGGER.getEffectiveLevel == logging.DEBUG or options.COMFY_DEBUG != "0" else subprocess.DEVNULL
    stderr = None if LOGGER.getEffectiveLevel == logging.INFO or options.COMFY_DEBUG != "0" else subprocess.DEVNULL
    COMFY_PROCESS = subprocess.Popen(run_cmd, stdout=stdout, stderr=stderr)  # pylint: disable=consider-using-with
    for _ in range(25):
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
