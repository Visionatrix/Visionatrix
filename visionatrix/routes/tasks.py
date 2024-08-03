import builtins
import json
import logging
import os
import shutil
import typing
from pathlib import Path

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    responses,
    status,
)

from .. import options
from ..flows import (
    Flow,
    flow_prepare_output_params,
    get_installed_flow,
    prepare_flow_comfy,
)
from ..pydantic_models import TaskRunResults, UserInfo, WorkerDetailsRequest
from ..tasks_engine import (
    TaskDetails,
    TaskDetailsShort,
    create_new_task,
    get_incomplete_task_without_error_database,
    get_task,
    get_task_files,
    get_tasks,
    get_tasks_short,
    put_task_in_queue,
    remove_task_by_id_database,
    remove_task_by_name,
    remove_task_files,
    remove_task_lock_database,
    remove_unfinished_task_by_id,
    remove_unfinished_tasks_by_name,
    task_restart_database,
    update_task_outputs,
    update_task_progress_database,
)
from ..tasks_engine_async import (
    create_new_task_async,
    get_incomplete_task_without_error_database_async,
    get_task_async,
    get_tasks_async,
    get_tasks_short_async,
    put_task_in_queue_async,
    task_restart_database_async,
    update_task_outputs_async,
    update_task_progress_database_async,
)

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/tasks", tags=["tasks"])
VALIDATE_PROMPT: typing.Callable[[dict], tuple[bool, dict, list, list]] | None = None


async def __task_run(
    name: str,
    input_params: dict,
    in_files: list[UploadFile | dict],
    flow: Flow,
    flow_comfy: dict,
    user_info: UserInfo,
    webhook_url: str | None,
    webhook_headers: dict | None,
    child_task: bool,
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
    task_details["webhook_url"] = webhook_url
    task_details["webhook_headers"] = webhook_headers
    if child_task:
        if not in_files or not isinstance(in_files[0], dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No input file provided. A child task can only be created from the node ID of the parent task.",
            ) from None
        task_details["parent_task_id"] = in_files[0]["task_id"]
        task_details["parent_task_node_id"] = in_files[0]["node_id"]
    flow_prepare_output_params(flow_validation[2], task_details["task_id"], task_details, flow_comfy)
    if options.VIX_MODE == "SERVER":
        await put_task_in_queue_async(task_details)
    else:
        put_task_in_queue(task_details)
    return task_details


@ROUTER.post("/create")
async def create_task(
    request: Request,
    name: str = Form(description="Name of the flow from which the task should be created"),
    count: int = Form(1, description="Number of tasks to be created"),
    input_params: str = Form(None, description="List of input parameters as an encoded json string"),
    webhook_url: str | None = Form(None, description="URL to call when task state changes"),
    webhook_headers: str | None = Form(None, description="Headers for webhook url as an encoded json string"),
    child_task: str = Form(0, description="Int boolean indicating whether to create a relation between tasks"),
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
    webhook_headers_dict = json.loads(webhook_headers) if webhook_headers else None
    for _ in range(count):
        task_details = await __task_run(
            name,
            input_params_dict,
            in_files,
            flow,
            flow_comfy,
            request.scope["user_info"],
            webhook_url,
            webhook_headers_dict,
            bool(child_task),
        )
        tasks_ids.append(task_details["task_id"])
        if "seed" in input_params_dict:
            input_params_dict["seed"] = input_params_dict["seed"] + 1
    try:
        return TaskRunResults.model_validate({"tasks_ids": tasks_ids})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Data validation error: {e}") from None


@ROUTER.get("/progress")
async def get_tasks_progress(
    request: Request,
    name: str = Query(None, description="Optional name to filter tasks by their name"),
) -> dict[int, TaskDetails]:
    """
    Retrieves the full tasks details information for a specific user. Optionally filter tasks by their name.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_tasks_async(name=name, user_id=request.scope["user_info"].user_id)
    else:
        r = get_tasks(name=name, user_id=request.scope["user_info"].user_id)
    return r


@ROUTER.get("/progress-summary")
async def get_tasks_progress_summary(
    request: Request,
    name: str = Query(None, description="Optional name to filter tasks by their name"),
) -> dict[int, TaskDetailsShort]:
    """
    Retrieves summary of the tasks progress details for a specific user. Optionally filter tasks by their name.
    """
    if options.VIX_MODE == "SERVER":
        r = await get_tasks_short_async(name=name, user_id=request.scope["user_info"].user_id)
    else:
        r = get_tasks_short(name=name, user_id=request.scope["user_info"].user_id)
    return r


@ROUTER.get("/progress/{task_id}")
async def get_task_progress(request: Request, task_id: int) -> TaskDetails:
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


@ROUTER.post(
    "/restart",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully restarted the specified task"},
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "examples": {
                        "Task already finished": {
                            "summary": "Task already finished",
                            "value": {"detail": "Task `{task_id}` already finished."},
                        },
                        "No error set": {
                            "summary": "No error set",
                            "value": {"detail": "Task `{task_id}` has no error set."},
                        },
                    }
                }
            },
        },
        404: {
            "description": "Task not found",
            "content": {"application/json": {"example": {"detail": "Task `{task_id}` was not found."}}},
        },
    },
)
async def restart_task(
    request: Request,
    task_id: int = Query(..., description="ID of the task to restart"),
    force: bool = Query(False, description="Force restart even if the task has no error"),
):
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if r["progress"] == 100.0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task `{task_id}` already finished.")
    if not r["error"] and not force:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task `{task_id}` has no error set.")

    if options.VIX_MODE == "SERVER":
        await task_restart_database_async(task_id)
    else:
        task_restart_database(task_id)
    remove_task_lock_database(task_id)


@ROUTER.delete(
    "/task",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully removed the specified task"},
        404: {
            "description": "Task not found",
            "content": {"application/json": {"example": {"detail": "Task `{task_id}` was not found."}}},
        },
    },
)
async def delete_task(request: Request, task_id: int = Query(..., description="ID of the task to remove")):
    """
    Removes a task from the system by the task ID.
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


@ROUTER.delete(
    "/clear",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully removed results of all finished tasks with the specified name"},
    },
)
async def clear_tasks(
    request: Request, name: str = Query(..., description="Name of the task whose results need to be deleted")
):
    """
    Removes all finished tasks associated with a specific task name, scoped to the requesting user.
    """
    remove_task_by_name(name, request.scope["user_info"].user_id)


@ROUTER.get(
    "/inputs",
    responses={
        200: {
            "description": "Successfully retrieved the input file",
            "content": {"application/octet-stream": {}},
        },
        404: {
            "description": "Task or input file not found",
            "content": {
                "application/json": {"example": {"detail": "Task(task_id): input file `file_name` was not found."}}
            },
        },
    },
)
async def get_task_inputs(
    request: Request,
    task_id: int = Query(..., description="ID of the task"),
    input_index: int = Query(..., description="Index of the input file"),
):
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if r["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    input_directory = os.path.join(options.TASKS_FILES_DIR, "input")
    for filename in os.listdir(input_directory):
        if filename == r["input_files"][input_index]["file_name"]:
            return responses.FileResponse(os.path.join(input_directory, filename))
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task({r['task_id']}): input file `{r['input_files'][input_index]['file_name']}` was not found.",
    )


@ROUTER.get(
    "/results",
    responses={
        200: {
            "description": "Successfully retrieved the result file",
            "content": {"application/octet-stream": {}},
        },
        404: {
            "description": "Task or result file not found",
            "content": {
                "application/json": {"example": {"detail": "Missing result for task=task_id and node=node_id."}}
            },
        },
    },
)
async def get_task_results(
    request: Request,
    task_id: int = Query(..., description="ID of the task"),
    node_id: int = Query(..., description="ID of the node"),
):
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    result_prefix = f"{task_id}_{node_id}_"
    output_files = get_task_files(task_id, "output")
    for output_file in output_files:
        if output_file[0].startswith(result_prefix):
            base_name, extension = os.path.splitext(output_file[0])
            content_disposition = base_name[:-1] + extension if base_name.endswith("_") else base_name + extension
            return responses.FileResponse(output_file[1], filename=content_disposition)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Missing result for task={task_id} and node={node_id}."
    )


@ROUTER.delete(
    "/queue",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully cleared unfinished tasks from the queue"},
    },
)
async def remove_tasks_from_queue(
    request: Request, name: str = Query(..., description="Name of the task to clear unfinished tasks from the queue")
):
    """
    Clears all unfinished tasks from the queue for a specific task name, scoped to the requesting user.
    """
    remove_unfinished_tasks_by_name(name, request.scope["user_info"].user_id)


@ROUTER.delete(
    "/queue/{task_id}",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully removed the unfinished task from the queue"},
        404: {
            "description": "Task not found",
            "content": {"application/json": {"example": {"detail": "Task `{task_id}` was not found."}}},
        },
    },
)
async def remove_task_from_queue(request: Request, task_id: int):
    """
    Removes a specific unfinished task from the queue using the task ID.
    """
    if get_task(task_id, request.scope["user_info"].user_id) is None:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    remove_unfinished_task_by_id(task_id)


@ROUTER.post(
    "/next",
    responses={
        200: {
            "description": "Successfully retrieved the task for the worker",
        },
        204: {
            "description": "No incomplete tasks available for the worker",
        },
    },
)
async def get_next_task(
    request: Request,
    worker_details: WorkerDetailsRequest = Body(...),
    tasks_names: list[str] = Body(..., description="List of task names the worker can handle"),
    last_task_name: str = Body("", description="Optional name of the last task the worker was working on"),
):
    """
    Retrieves an incomplete task for a `worker` to process. Workers provide a list of tasks names they can handle
    and optionally the name of the last task they were working on to prioritize similar types of tasks. If a
    worker is associated with an admin account, it can retrieve tasks regardless of user assignment; otherwise,
    it retrieves only those assigned to the user.
    """
    user_id = None if request.scope["user_info"].is_admin else request.scope["user_info"].user_id
    if options.VIX_MODE == "SERVER":
        task = await get_incomplete_task_without_error_database_async(
            request.scope["user_info"].user_id, worker_details, tasks_names, last_task_name, user_id
        )
    else:
        task = get_incomplete_task_without_error_database(
            request.scope["user_info"].user_id, worker_details, tasks_names, last_task_name, user_id
        )
    if not task:
        return responses.Response(status_code=status.HTTP_204_NO_CONTENT)
    return task


async def __webhook_task_progress(
    url: str, headers: dict | None, task_id: int, progress: float, execution_time: float, error: str
) -> None:
    async with httpx.AsyncClient(base_url=url, timeout=3.0) as client:
        await client.post(
            url="task-progress",
            json={
                "task_id": task_id,
                "progress": progress,
                "execution_time": execution_time,
                "error": error,
            },
            headers=headers,
        )


@ROUTER.put(
    "/progress",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {
            "description": "Task progress updated successfully",
        },
        400: {
            "description": "Failed to update task progress",
            "content": {"application/json": {"example": {"detail": "Failed to update task progress."}}},
        },
        404: {
            "description": "Task not found or not authorized",
            "content": {"application/json": {"example": {"detail": "Task `{task_id}` was not found."}}},
        },
    },
)
async def update_task_progress(
    b_tasks: BackgroundTasks,
    request: Request,
    worker_details: WorkerDetailsRequest = Body(...),
    task_id: int = Body(..., description="ID of the task to update progress for"),
    progress: float = Body(..., description="Progress percentage of the task"),
    execution_time: float = Body(..., description="Execution time of the task in seconds"),
    error: str = Body("", description="Error message if any"),
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
    if not update_success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update task progress.")
    if r["webhook_url"]:
        b_tasks.add_task(
            __webhook_task_progress, r["webhook_url"], r["webhook_headers"], task_id, progress, execution_time, error
        )


@ROUTER.put(
    "/results",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully saved task results"},
        404: {
            "description": "Task not found",
            "content": {"application/json": {"example": {"detail": "Task `{task_id}` was not found."}}},
        },
        400: {
            "description": "Bad request",
            "content": {"application/json": {"example": {"detail": "result_file.filename does not belong to task."}}},
        },
    },
)
async def set_task_results(
    request: Request,
    task_id: int = Query(..., description="The ID of the task to save results for"),
    files: list[UploadFile] = Form(..., description="List of result files to save"),  # noqa
):
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
    for result_file in files:
        node_found_in_flow = False
        for task_output in r["outputs"]:
            task_file_prefix = f"{task_id}_{task_output['comfy_node_id']}_"
            if result_file.filename.startswith(task_file_prefix):
                task_output["file_size"] = result_file.size
                node_found_in_flow = True
                break
        if not node_found_in_flow:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{result_file.filename} does not belong to task.",
            )
        try:
            file_path = Path(output_directory).joinpath(result_file.filename)
            with builtins.open(file_path, mode="wb") as out_file:
                shutil.copyfileobj(result_file.file, out_file)
        finally:
            result_file.file.close()

    if options.VIX_MODE == "SERVER":
        await update_task_outputs_async(task_id, r["outputs"])
    else:
        update_task_outputs(task_id, r["outputs"])


@ROUTER.delete(
    "/lock",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully removed task lock"},
        404: {
            "description": "Task not found",
            "content": {"application/json": {"example": {"detail": "Task `{task_id}` was not found."}}},
        },
    },
)
async def remove_task_lock(
    request: Request, task_id: int = Query(..., description="The ID of the task to remove the lock from")
):
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
