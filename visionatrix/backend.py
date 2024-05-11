import base64
import builtins
import copy
import fnmatch
import json
import logging
import os
import shutil
import signal
import threading
import time
import typing
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import (
    BackgroundTasks,
    Body,
    FastAPI,
    Form,
    HTTPException,
    Request,
    UploadFile,
    responses,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send

from . import comfyui, database, options
from .flows import (
    Flow,
    flow_prepare_output_params,
    get_available_flows,
    get_installed_flow,
    get_installed_flows,
    get_not_installed_flows,
    install_custom_flow,
    prepare_flow_comfy,
    uninstall_flow,
)
from .pydantic_models import TaskRunResults, WorkerDetails
from .tasks_engine import (
    TaskDetails,
    TaskDetailsShort,
    background_prompt_executor,
    create_new_task,
    create_new_task_async,
    get_incomplete_task_without_error_database,
    get_task,
    get_task_async,
    get_tasks,
    get_tasks_async,
    get_tasks_short,
    get_tasks_short_async,
    put_task_in_queue,
    put_task_in_queue_async,
    remove_active_task_lock,
    remove_task_by_id_database,
    remove_task_by_name,
    remove_task_files,
    remove_task_lock_database,
    remove_unfinished_task_by_id,
    remove_unfinished_tasks_by_name,
    start_tasks_engine,
    task_progress_callback,
    task_restart_database,
    task_restart_database_async,
    update_task_progress_database,
    update_task_progress_database_async,
)

LOGGER = logging.getLogger("visionatrix")
FLOW_INSTALL_STATUS = {}  # {flow_name: {progress: float, error: ""}}
EXIT_EVENT = threading.Event()
VALIDATE_PROMPT: typing.Callable[[dict], tuple[bool, dict, list, list]]


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
                authorization: str = conn.headers.get("Authorization")
                if not authorization:
                    await bad_auth_response(scope, receive, send)
                    return

                try:
                    scheme, encoded_credentials = authorization.split()
                    if scheme.lower() != "basic":
                        await bad_auth_response(scope, receive, send)
                        return

                    decoded_credentials = base64.b64decode(encoded_credentials).decode("ascii")
                    username, _, password = decoded_credentials.partition(":")
                    if (userinfo := await database.get_user(username, password)) is None or userinfo.disabled is True:
                        await bad_auth_response(scope, receive, send)
                        return
                except ValueError:
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
    global VALIDATE_PROMPT
    VALIDATE_PROMPT, comfy_queue = comfyui.load(task_progress_callback)
    await start_tasks_engine(comfy_queue, EXIT_EVENT)
    if options.UI_DIR:
        app.mount("/", StaticFiles(directory=options.UI_DIR, html=True), name="client")
    yield
    EXIT_EVENT.set()
    comfyui.interrupt_processing()


APP = FastAPI(lifespan=lifespan)
APP.add_middleware(VixAuthMiddleware)
if cors_origins := os.getenv("CORS_ORIGINS", "").split(","):
    APP.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@APP.get("/flows-installed")
async def flows_installed() -> list[Flow]:
    """
    Return the list of installed flows. Each flow can potentially be converted into a task. The response
    includes details such as the name, display name, description, author, homepage URL, and other relevant
    information about each flow.
    """
    return get_installed_flows()


@APP.get("/flows-available")
async def flows_available() -> list[Flow]:
    """
    Return the list of flows that can be installed. This endpoint provides detailed information about each flow,
    similar to the installed flows, which includes metadata and configuration parameters.
    """
    return get_not_installed_flows()


@APP.get("/flows-sub-flows")
async def flows_from(input_type: typing.Literal["image", "video"]) -> list[Flow]:
    """
    Retrieves a list of flows designed to post-process the results from other flows, filtering by the type
    of input they handle, either 'image' or 'video'. This endpoint is particularly useful for chaining workflows
    where the output of one flow becomes the input to another. It modifies the main flow's structure by adopting
    sub-flow's display name and selectively merging input parameters from the sub-flows into the main flow's parameters
    based on matching names.
    """
    r = []
    for i in get_installed_flows():
        for sub_flow in i.sub_flows:
            if sub_flow.type == input_type:
                transformed_flow = copy.deepcopy(i)
                transformed_flow.display_name = sub_flow.display_name
                for sub_flow_input_params in sub_flow.input_params:
                    for k2 in transformed_flow.input_params:
                        if k2["name"] == sub_flow_input_params["name"]:
                            k2.update(**sub_flow_input_params)
                            break
                r.append(transformed_flow)
    return r


@APP.put("/flow")
def flow_install(request: Request, b_tasks: BackgroundTasks, name: str):
    """
    Endpoint to initiate the installation of a flow based on its name. This endpoint requires admin privileges
    to perform the installation. If another flow installation is already in progress, it prevents a new
    installation to avoid conflicts, returning a 409 Conflict HTTP status.

    This endpoint schedules a background task for the installation process using the specified flow name. It
    checks the availability of the flow in the list of available flows and starts the installation if the flow
    is found. It ensures that no two installations can run concurrently.
    """
    __require_admin(request)
    if any(i for i in FLOW_INSTALL_STATUS.values() if i["progress"] < 100.0 and i["error"] == ""):
        return responses.JSONResponse(status_code=409, content={"error": "Another flow installation is in progress."})

    flows_comfy = []
    flows = get_available_flows(flows_comfy)
    for i, flow in enumerate(flows):
        if flow.name == name:
            FLOW_INSTALL_STATUS[name] = {"progress": 0.0, "error": ""}
            b_tasks.add_task(install_custom_flow, flow, flows_comfy[i], __progress_install_callback)
            return responses.JSONResponse(content={"error": ""})
    return responses.JSONResponse(content={"error": f"Can't find `{name}` flow."})


@APP.get("/flow-progress-install")
async def flow_progress_install():
    """
    Retrieves the current installation progress of all flows from an in-memory dictionary. This endpoint
    returns a dictionary showing the installation status for each flow.

    Status is not persistent and will be reset upon restart
    """
    return responses.JSONResponse(content=FLOW_INSTALL_STATUS)


@APP.delete("/flow")
async def flow_delete(request: Request, name: str):
    """
    Endpoint to delete an installed flow by its name. Requires administrative privileges to execute.
    """
    __require_admin(request)
    uninstall_flow(name)
    return responses.JSONResponse(content={"error": ""})


async def __task_run(
    name: str,
    input_params: dict,
    in_files: list[UploadFile | dict],
    flow: Flow,
    flow_comfy: dict,
    user_info: database.UserInfo,
):
    if options.VIX_MODE == "SERVER":
        task_details = await create_new_task_async(name, input_params, user_info)
    else:
        task_details = create_new_task(name, input_params, user_info)
    try:
        flow_comfy = prepare_flow_comfy(flow, flow_comfy, input_params, in_files, task_details)
    except RuntimeError as e:
        remove_task_files(task_details["task_id"], ["input"])
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None

    flow_validation: [bool, dict, list, list] = VALIDATE_PROMPT(flow_comfy)
    if not flow_validation[0]:
        remove_task_files(task_details["task_id"], ["input"])
        LOGGER.error("Flow validation error: %s\n%s", flow_validation[1], flow_validation[3])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Bad Flow: `{flow_validation[1]}`"
        ) from None
    task_details["flow_comfy"] = flow_comfy
    flow_prepare_output_params(flow_validation[2], task_details["task_id"], task_details, flow_comfy)
    if options.VIX_MODE == "SERVER":
        await put_task_in_queue_async(task_details)
    else:
        put_task_in_queue(task_details)
    return task_details


@APP.post("/task")
async def task_run(
    request: Request,
    name: str = Form(description="Name of the flow from which the task should be created"),
    count: int = Form(1, description="Number of tasks to be created"),
    input_params: str = Form(None, description="List of input parameters as an encoded json string"),
    files: list[UploadFile | str] = Form(None, description="List of input files for flow"),  # noqa
) -> TaskRunResults:
    """
    Endpoint to initiate the creation and execution of tasks within the Vix workflow environment,
    handling both file inputs and task-related parameters.
    """
    in_files = []
    for i in files if files else []:
        if isinstance(i, str):
            try:
                input_file_info = json.loads(i)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid files input:{i}"
                ) from None
            if "task_id" not in input_file_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Missing `task_id` parameter"
                ) from None
            if not get_task(int(input_file_info["task_id"]), request.scope["user_info"].user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing task with id={input_file_info['task_id']}",
                ) from None
            in_files.append(input_file_info)
        else:
            in_files.append(i)
    try:
        input_params_dict = json.loads(input_params) if input_params else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON format for params") from None
    if "seed" in input_params_dict:
        input_params_dict["seed"] = int(input_params_dict["seed"])

    flow_comfy = {}
    flow = get_installed_flow(name, flow_comfy)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Flow `{name}` is not installed.") from None
    tasks_ids = []
    for _ in range(count):
        task_details = await __task_run(name, input_params_dict, in_files, flow, flow_comfy, request.scope["user_info"])
        tasks_ids.append(task_details["task_id"])
        if "seed" in input_params_dict:
            input_params_dict["seed"] = input_params_dict["seed"] + 1
    try:
        return TaskRunResults.model_validate({"tasks_ids": tasks_ids})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Data validation error: {e}") from None


@APP.get("/tasks-progress")
async def tasks_progress(request: Request, name: str | None = None) -> dict[int, TaskDetails]:
    """
    Retrieves the full tasks details information for a specific user. Optionally filter tasks by their name.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_tasks_async(name=name, user_id=request.scope["user_info"].user_id)
    else:
        r = get_tasks(name=name, user_id=request.scope["user_info"].user_id)
    return r


@APP.get("/tasks-progress-short")
async def tasks_progress_short(request: Request, name: str | None = None) -> dict[int, TaskDetailsShort]:
    """
    Retrieves summary of the tasks progress details for a specific user. Optionally filter tasks by their name.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_tasks_short_async(name=name, user_id=request.scope["user_info"].user_id)
    else:
        r = get_tasks_short(name=name, user_id=request.scope["user_info"].user_id)
    return r


@APP.get("/task-progress")
async def task_progress(request: Request, task_id: int) -> TaskDetails:
    """
    Retrieves the full task details of a specified task by task ID.
    Access is restricted to the task owner or an administrator.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_task_async(task_id, request.scope["user_info"].user_id)
    else:
        r = get_task(task_id, request.scope["user_info"].user_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    try:
        return TaskDetails.model_validate(r)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Data validation error: {e}") from None


@APP.post("/task-restart")
async def task_restart(request: Request, task_id: int, force: bool = False):
    """
    Restarts a task specified by `task_id` if it has encountered an error or is not yet completed.
    Only tasks that have errors can be restarted unless `force` is set to `True`,
    which allows restarting any non-completed tasks.
    This endpoint checks the task's current status and resets its progress, allowing it to be re-executed.
    Access to this action is restricted to the task's owner or an administrator.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_task_async(task_id, request.scope["user_info"].user_id)
    else:
        r = get_task(task_id, request.scope["user_info"].user_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    if r["progress"] == 100.0:
        return responses.JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": f"Task `{task_id}` already finished."}
        )
    if not r["error"] and not force:
        return responses.JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": f"Task `{task_id}` has no error set."}
        )

    if options.VIX_MODE == "SERVER":
        await task_restart_database_async(task_id)
    else:
        task_restart_database(task_id)
    remove_task_lock_database(task_id)
    return responses.JSONResponse(content={"error": ""})


@APP.delete("/task")
async def task_remove(request: Request, task_id: int):
    """
    Removes a finished or errored task from the system using the task ID.
    Access is limited to the task owner or administrators.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_task_async(task_id)
    else:
        r = get_task(task_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    if r["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    remove_task_by_id_database(task_id)
    return responses.JSONResponse(content={"error": ""})


@APP.delete("/tasks")
async def tasks_remove(request: Request, name: str):
    """
    Removes all finished or errored tasks associated with a specific task name, scoped to the requesting user.
    """
    remove_task_by_name(name, request.scope["user_info"].user_id)
    return responses.JSONResponse(content={"error": ""})


@APP.get("/task-inputs")
async def task_inputs(request: Request, task_id: int, input_index: int):
    """
    Retrieves a specific input file for a task, identified by `task_id` and `input_index`. This endpoint
    allows access to input files regardless of whether the task is in queue or has finished. The input index
    is used to select among multiple input files if more than one was provided for the task.
    Administrators can access inputs of any task, while regular users can only access inputs of their own tasks.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_task_async(task_id)
    else:
        r = get_task(task_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    if r["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    input_directory = os.path.join(options.TASKS_FILES_DIR, "input")
    for filename in os.listdir(input_directory):
        if filename == r["input_files"][input_index]:
            return responses.FileResponse(os.path.join(input_directory, filename))
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task({r['task_id']}): input file `{r['input_files'][input_index]}` was not found.",
    )


@APP.get("/task-results")
async def task_results(request: Request, task_id: int, node_id: int):
    """
    Retrieves the result file associated with a specific task and node ID. This function searches for
    output files in the designated output directory that match the task and node identifiers.
    If the specific result file is not found, or if the task does not exist, 404 HTTP error is returned.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_task_async(task_id, request.scope["user_info"].user_id)
    else:
        r = get_task(task_id, request.scope["user_info"].user_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    result_prefix = f"{task_id}_{node_id}_"
    output_directory = os.path.join(options.TASKS_FILES_DIR, "output")
    for filename in os.listdir(output_directory):
        if filename.startswith(result_prefix):
            base_name, extension = os.path.splitext(filename)
            content_disposition = base_name[:-1] + extension if base_name.endswith("_") else base_name + extension
            return responses.FileResponse(os.path.join(output_directory, filename), filename=content_disposition)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Missing result for task={task_id} and node={node_id}."
    )


@APP.delete("/tasks-queue")
async def tasks_queue_clear(request: Request, name: str):
    """
    Clears all unfinished tasks from the queue for a specific task name, scoped to the requesting user.
    """
    remove_unfinished_tasks_by_name(name, request.scope["user_info"].user_id)
    return responses.JSONResponse(content={"error": ""})


@APP.delete("/task-queue")
async def task_queue_clear(request: Request, task_id: int):
    """
    Removes a specific unfinished task from the queue using the task ID, scoped to the requesting user.
    """
    if get_task(task_id, request.scope["user_info"].user_id) is None:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    remove_unfinished_task_by_id(task_id)
    return responses.JSONResponse(content={"error": ""})


@APP.post("/task-worker/get")
async def task_worker_give_task(
    request: Request,
    worker_details: typing.Annotated[WorkerDetails, Body()],
    tasks_names: typing.Annotated[list[str], Body()],
    last_task_name: typing.Annotated[str, Body()] = "",
):
    """
    Retrieves an incomplete task for a `worker` to process. Workers provide a list of tasks names they can handle
    and optionally the name of the last task they were working on to prioritize similar types of tasks. If a
    worker is associated with an admin account, it can retrieve tasks regardless of user assignment; otherwise,
    it retrieves only those assigned to the user.
    """
    user_id = None if request.scope["user_info"].is_admin else request.scope["user_info"].user_id
    return responses.JSONResponse(
        content={
            "error": "",
            "task": get_incomplete_task_without_error_database(
                request.scope["user_info"].user_id, worker_details, tasks_names, last_task_name, user_id
            ),
        }
    )


@APP.put("/task-worker/progress")
async def task_worker_update_progress(
    request: Request,
    worker_details: typing.Annotated[WorkerDetails, Body()],
    task_id: typing.Annotated[int, Body()],
    progress: typing.Annotated[float, Body()],
    execution_time: typing.Annotated[float, Body()],
    error: typing.Annotated[str, Body()] = "",
):
    """
    Updates the progress of a specific task identified by `task_id`. This endpoint checks if the task exists
    and if the requester is authorized to update its progress. If the task is not found or unauthorized,
    a 404 HTTP error is raised, and `worker` should stop and consider the task canceled.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_task_async(task_id)
    else:
        r = get_task(task_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if r["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if options.VIX_MODE == "SERVER":
        update_success = await update_task_progress_database_async(
            task_id, progress, error, execution_time, request.scope["user_info"].user_id, worker_details
        )
    else:
        update_success = update_task_progress_database(
            task_id, progress, error, execution_time, request.scope["user_info"].user_id, worker_details
        )
    return responses.JSONResponse(content={"error": "" if update_success else "failed to update"})


@APP.put("/task-worker/results")
async def task_worker_put_results(request: Request, task_id: int, files: list[UploadFile]):
    """
    Saves the result files for a specific task on the server. This endpoint checks if the task exists
    and if the `worker` making the request has the authorization to upload results.
    If the task is not found or unauthorized, a 404 HTTP error is raised.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_task_async(task_id)
    else:
        r = get_task(task_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if r["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    output_directory = os.path.join(options.TASKS_FILES_DIR, "output")
    for r in files:
        try:
            with builtins.open(Path(output_directory).joinpath(r.filename), mode="wb") as out_file:
                shutil.copyfileobj(r.file, out_file)
        finally:
            r.file.close()
    return responses.JSONResponse(content={"error": ""})


@APP.delete("/task-worker/lock")
async def task_worker_remove_lock(request: Request, task_id: int):
    """
    Unlocks a task specified by the `task_id`. This endpoint checks if the task exists
    and if the `worker` making the request has the authorization to unlock it.
    If the task is not found or unauthorized, a 404 HTTP error is raised.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_task_async(task_id)
    else:
        r = get_task(task_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if r["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    remove_task_lock_database(task_id)
    return responses.JSONResponse(content={"error": ""})


@APP.post("/engine-interrupt")
async def engine_interrupt(request: Request, b_tasks: BackgroundTasks):
    """
    Interrupts the currently executing task. This is primarily an internal function and should be used
    cautiously. For standard task management, prefer using the `task_queue_clear` or `tasks_queue_clear`
    endpoints. Requires administrative privileges to execute.
    """

    def __interrupt_task():
        comfyui.interrupt_processing()

    __require_admin(request)
    if options.VIX_MODE != "SERVER":
        b_tasks.add_task(__interrupt_task)
    return responses.JSONResponse(content={"error": ""})


@APP.post("/shutdown")
async def shutdown(request: Request, b_tasks: BackgroundTasks):
    """
    Shuts down the current instance of Vix. This endpoint queues a task to terminate the server process
    after a short delay, ensuring any final operations can complete. Access is restricted to administrators only.
    """

    def __shutdown_vix():
        time.sleep(1.0)
        os.kill(os.getpid(), signal.SIGINT)

    __require_admin(request)
    b_tasks.add_task(__shutdown_vix)
    return responses.JSONResponse(content={"error": ""})


# TO-DO: remove this, no needed
@APP.get("/system_stats")
async def system_stats():
    return responses.JSONResponse(content=comfyui.get_worker_details())


def run_vix(*args, **kwargs) -> None:
    if options.VIX_MODE == "WORKER" and options.UI_DIR:
        LOGGER.error("`WORKER` mode is incompatible with UI")
        return

    for i in ("input", "output"):
        os.makedirs(os.path.join(options.TASKS_FILES_DIR, i), exist_ok=True)

    if options.VIX_MODE != "WORKER":
        try:
            uvicorn.run(
                APP,
                *args,
                host=options.VIX_HOST if options.VIX_HOST else "127.0.0.1",
                port=int(options.VIX_PORT) if options.VIX_PORT else 8288,
                **kwargs,
            )
        except KeyboardInterrupt:
            print("Visionatrix is shutting down.")
    else:
        _, comfy_queue = comfyui.load(task_progress_callback)
        if not options.VIX_SERVER:
            database.init_database_engine()  # we get tasks directly from the Database

        try:
            background_prompt_executor(comfy_queue, EXIT_EVENT)
        except KeyboardInterrupt:
            remove_active_task_lock()
            print("Visionatrix is shutting down.")


def __progress_install_callback(name: str, progress: float, error: str) -> None:
    FLOW_INSTALL_STATUS[name] = {"progress": progress, "error": error}


def __require_admin(request: Request) -> None:
    if not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin privilege required") from None
