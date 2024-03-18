import json
import logging
import os
import signal
import time
from contextlib import asynccontextmanager

import httpx

from . import options
from .flows import (
    get_available_flows,
    get_installed_flow,
    get_installed_flows,
    get_not_installed_flows,
    install_custom_flow,
    prepare_flow_comfy,
    uninstall_flow,
)
from .tasks_engine import (
    create_new_task,
    get_task,
    get_tasks,
    get_tasks_from_queue,
    load_tasks,
    put_task_in_queue,
    remove_task,
    remove_task_files,
    save_tasks,
    start_tasks_engine,
    stop_tasks_engine,
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
        await start_tasks_engine(backend_dir, tasks_files_dir)
        if ui_dir:
            try:
                _app.mount("/", fastapi.staticfiles.StaticFiles(directory=ui_dir, html=True), name="client")
            except RuntimeError:
                await stop_tasks_engine()
                raise
            load_tasks(tasks_files_dir)
        yield
        await stop_tasks_engine()
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
    async def task_run(
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
            remove_task_files(task_id, tasks_files_dir, ["input"])
            raise fastapi.HTTPException(status_code=400, detail=str(e)) from None

        # TO-DO: it will be good to run ComfyUI in the current process and not in a separate one.
        # add ComfyUI directory to path
        # from ..amw_backend.execution import validate_prompt
        # sys.path.append(backend_dir)
        # from execution import validate_prompt
        #
        # flow_validation: [bool, dict, list, list] = validate_prompt(flow_comfy)  # noqa
        # if not flow_validation[0]:
        #     remove_task_files(task_id, backend_dir, ["input"])
        #     LOGGER.error("Flow validation error: %s\n%s", flow_validation[1], flow_validation[3])
        #     raise fastapi.HTTPException(status_code=400, detail=f"Bad Flow: `{flow_validation[1]}`") from None
        task_details["flow_comfy"] = flow_comfy
        put_task_in_queue(task_id, task_details)
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
        tasks = get_tasks_from_queue()
        delete_keys = []
        for k, v in tasks.items():
            if not name or v["name"] == name and v["progress"] != 100.0:
                v["interrupt"] = True
                delete_keys.append(k)
        for k in delete_keys:
            tasks.pop(k, None)
            remove_task_files(k, tasks_files_dir, ["output", "input"])
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.delete("/task-queue")
    async def task_queue_clear(task_id: int):
        remove_task(task_id, tasks_files_dir)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.post("/engine-interrupt")
    async def engine_interrupt(b_tasks: fastapi.BackgroundTasks):
        async def __interrupt_task():
            await httpx.AsyncClient().post(url=f"http://{options.get_comfy_address()}/interrupt")

        b_tasks.add_task(__interrupt_task)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.post("/engine-restart")
    async def engine_restart():
        await stop_tasks_engine()
        await start_tasks_engine(backend_dir, tasks_files_dir)
        return fastapi.responses.JSONResponse(content={"error": ""})

    @app.post("/shutdown")
    async def shutdown(b_tasks: fastapi.BackgroundTasks):
        def __shutdown_vix():
            time.sleep(1.0)
            os.kill(os.getpid(), signal.SIGINT)

        await stop_tasks_engine()
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


def __progress_install_callback(name: str, progress: float, error: str) -> None:
    FLOW_INSTALL_STATUS[name] = {"progress": progress, "error": error}
