import asyncio
import json
import logging
import os
import signal
import time
import typing
from contextlib import asynccontextmanager

import uvicorn
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, UploadFile, responses
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import comfyui, options
from .flows import (
    flow_prepare_output_params,
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
    put_task_in_queue,
    remove_task_by_id,
    remove_task_by_name,
    remove_task_files,
    remove_unfinished_task_by_id,
    remove_unfinished_tasks_by_name,
    start_tasks_engine,
    task_progress_callback,
)

LOGGER = logging.getLogger("visionatrix")
FLOW_INSTALL_STATUS = {}  # {flow_name: {progress: float, error: ""}}
EXIT_EVENT = asyncio.Event()
VALIDATE_PROMPT: typing.Callable[[dict], tuple[bool, dict, list, list]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global VALIDATE_PROMPT
    VALIDATE_PROMPT, comfy_queue = comfyui.load(task_progress_callback)
    await start_tasks_engine(comfy_queue, EXIT_EVENT)
    if options.UI_DIR:
        app.mount("/", StaticFiles(directory=options.UI_DIR, html=True), name="client")
    yield
    EXIT_EVENT.set()
    comfyui.interrupt_processing()


APP = FastAPI(lifespan=lifespan)
if cors_origins := os.getenv("CORS_ORIGINS", "").split(","):
    APP.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@APP.get("/flows-installed")
async def flows_installed():
    return responses.JSONResponse(content=get_installed_flows())


@APP.get("/flows-available")
async def flows_available():
    return responses.JSONResponse(content=get_not_installed_flows())


@APP.put("/flow")
def flow_install(b_tasks: BackgroundTasks, name: str):
    flows, flows_comfy = get_available_flows()
    for i, flow in enumerate(flows):
        if flow["name"] == name:
            FLOW_INSTALL_STATUS[name] = {"progress": 0.0, "error": ""}
            b_tasks.add_task(install_custom_flow, flow, flows_comfy[i], __progress_install_callback)
            return responses.JSONResponse(content={"error": ""})
    return responses.JSONResponse(content={"error": f"Can't find `{name}` flow."})


@APP.get("/flow-progress-install")
async def flow_progress_install():
    return responses.JSONResponse(content=FLOW_INSTALL_STATUS)


@APP.delete("/flow")
async def flow_delete(name: str):
    uninstall_flow(name)
    return responses.JSONResponse(content={"error": ""})


@APP.post("/task")
async def task_run(
    name: str = Form(),
    input_params: str = Form(None),
    files: list[UploadFile] = None,  # noqa
):
    in_files = [i.file for i in files] if files else []
    try:
        input_params_list = json.loads(input_params) if input_params else []
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for params") from None

    flow_comfy = {}
    flow = get_installed_flow(name, flow_comfy)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow `{name}` is not installed.") from None

    task_details = create_new_task(name, input_params_list)
    try:
        flow_comfy = prepare_flow_comfy(flow, flow_comfy, input_params_list, in_files, task_details)
    except RuntimeError as e:
        remove_task_files(task_details["task_id"], ["input"])
        raise HTTPException(status_code=400, detail=str(e)) from None

    flow_validation: [bool, dict, list, list] = VALIDATE_PROMPT(flow_comfy)
    if not flow_validation[0]:
        remove_task_files(task_details["task_id"], ["input"])
        LOGGER.error("Flow validation error: %s\n%s", flow_validation[1], flow_validation[3])
        raise HTTPException(status_code=400, detail=f"Bad Flow: `{flow_validation[1]}`") from None
    task_details["flow_comfy"] = flow_comfy
    flow_prepare_output_params(flow_validation[2], task_details["task_id"], task_details, flow_comfy)
    put_task_in_queue(task_details)
    return responses.JSONResponse(content={"task_id": str(task_details["task_id"])})


@APP.get("/tasks-progress")
async def tasks_progress():
    return responses.JSONResponse(content=get_tasks())


@APP.get("/task-progress")
async def task_progress(task_id: int):
    if (r := get_task(task_id)) is None:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    return responses.JSONResponse(content=r)


@APP.delete("/task")
async def task_remove(task_id: int):
    remove_task_by_id(task_id)
    return responses.JSONResponse(content={"error": ""})


@APP.delete("/tasks")
async def tasks_remove(name: str):
    remove_task_by_name(name)
    return responses.JSONResponse(content={"error": ""})


@APP.get("/task-results")
async def task_results(task_id: str, node_id: int):
    result_prefix = f"{task_id}_{node_id}_"
    output_directory = os.path.join(options.TASKS_FILES_DIR, "output")
    for filename in os.listdir(output_directory):
        if filename.startswith(result_prefix):
            return responses.FileResponse(os.path.join(output_directory, filename))
    raise HTTPException(status_code=404, detail=f"Missing result for task={task_id} and node={node_id}.")


@APP.delete("/tasks-queue")
async def tasks_queue_clear(name: str):
    remove_unfinished_tasks_by_name(name)
    return responses.JSONResponse(content={"error": ""})


@APP.delete("/task-queue")
async def task_queue_clear(task_id: int):
    remove_unfinished_task_by_id(task_id)
    return responses.JSONResponse(content={"error": ""})


@APP.post("/engine-interrupt")
async def engine_interrupt(b_tasks: BackgroundTasks):
    def __interrupt_task():
        comfyui.interrupt_processing()

    b_tasks.add_task(__interrupt_task)
    return responses.JSONResponse(content={"error": ""})


@APP.post("/shutdown")
async def shutdown(b_tasks: BackgroundTasks):
    def __shutdown_vix():
        time.sleep(1.0)
        os.kill(os.getpid(), signal.SIGINT)

    b_tasks.add_task(__shutdown_vix)
    return responses.JSONResponse(content={"error": ""})


@APP.get("/system_stats")
async def system_stats():
    return responses.JSONResponse(content=comfyui.system_stats())


def run_backend(*args, **kwargs) -> None:
    for i in ("input", "output"):
        os.makedirs(os.path.join(options.TASKS_FILES_DIR, i), exist_ok=True)

    try:
        uvicorn.run(APP, *args, host=options.VIX_HOST, port=options.VIX_PORT, **kwargs)
    except KeyboardInterrupt:
        print("Visionatrix is shutting down.")


def __progress_install_callback(name: str, progress: float, error: str) -> None:
    FLOW_INSTALL_STATUS[name] = {"progress": progress, "error": error}
