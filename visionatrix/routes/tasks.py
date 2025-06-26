import asyncio
import builtins
import logging
import os
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Form, HTTPException
from fastapi import Path as FastApiPath
from fastapi import Query, Request, UploadFile, responses, status

from .. import options
from ..pydantic_models import (
    ExecutionDetails,
    TaskCreationWithFullParams,
    TaskDetails,
    TaskDetailsShort,
    TaskRunResults,
    TaskUpdateRequest,
    WorkerDetailsRequest,
)
from ..tasks_engine import (
    collect_child_task_ids,
    get_incomplete_task_without_error_database,
    get_task_files,
    remove_task_by_id_database,
    remove_task_lock_database,
    remove_unfinished_task_by_id,
    remove_unfinished_tasks_by_name_and_group,
    update_task_progress_database,
)
from ..tasks_engine_async import (
    get_task_async,
    get_tasks_async,
    get_tasks_short_async,
    task_restart_database_async,
    update_task_info_database_async,
    update_task_outputs_async,
)
from ..webhooks import webhook_task_progress
from .tasks_internal import (
    create_task_logic,
    get_files_for_node,
    zip_files_as_response,
)

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/tasks", tags=["tasks"])  # if you change the prefix, also change it in custom_openapi.py


@ROUTER.put("/create/{name}")
async def create_task(
    request: Request,
    name: Annotated[str, FastApiPath(title="Name of the flow from which the task should be created")],
    data: Annotated[TaskCreationWithFullParams, Form()],
) -> TaskRunResults:
    """
    Endpoint to initiate the creation and execution of tasks from the flows.

    **Path Parameter:**

    - `name`: Name of the flow from which the task should be created

    **Reserved Form Fields:**

    - `group_scope`: Group number to which task should be assigned. Maximum value is 255
    - `priority`: Task execution priority. Higher numbers indicate higher priority. Maximum value is 15
    - `child_task`: Int boolean indicating whether to create a relation between tasks
    - `webhook_url`: Optional. URL to call when task state changes
    - `webhook_headers`: Optional. Headers for webhook URL as encoded JSON string. Used only when `webhook_url` is set
    - `count`: Number of tasks to be created
    - `translate`: Should the prompt be translated if auto-translation option is enabled

    **Dynamic Task Parameters:**

    All other form fields will be considered as **dynamic task-specific input parameters**.
    These parameters vary depending on the flow specified by `name` and can be either text parameters or input files.

    **Custom Headers (Admin Only):**

    - `X-WORKER-UNLOAD-MODELS`: If `1`, unloads all models from memory before task execution.
    - `X-WORKER-EXECUTION-PROFILER`: If `1`, enables detailed profiling of task execution.
    - `X-WORKER-ID`: Forces the tasks to be assigned to a specific worker.
    - `X-FEDERATED-TASK`: If `1`, requires X-WORKER-ID`, rejects the task if the worker is busy, mark task as hidden.

    **Response:**

    - Returns a `TaskRunResults` object containing the list of task IDs and the outputs for the created tasks.

    **Notes:**

    - The request must use `multipart/form-data` as the content type.
    - Dynamic parameters should correspond to the inputs expected by the specified flow.
    - If a parameter is expected to be a file, include it as a file upload in the form data.
    - If a parameter is expected to be text, include it as a regular form field.
    - The endpoint accepts both text and file inputs as dynamic parameters.
    """

    created_tasks = await create_task_logic(request, name, data)
    tasks_ids = [td["task_id"] for td in created_tasks]
    outputs = created_tasks[0]["outputs"] if created_tasks else None
    try:
        return TaskRunResults.model_validate({"tasks_ids": tasks_ids, "outputs": outputs})
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Data validation error: {e}") from None


@ROUTER.put("/create-sync/{name}", response_class=responses.Response)
async def create_task_sync(
    request: Request,
    name: Annotated[str, FastApiPath(title="Name of the flow from which the task should be created")],
    data: Annotated[TaskCreationWithFullParams, Form()],
    cleanup: bool = Query(True, description="If true, the task record and its files will be deleted after completion."),
    timeout: int = Query(600, description="Timeout in seconds for task completion.", ge=5),
):
    """
    Synchronously creates and executes a task, returning the results directly.

    This endpoint behaves like `/create/{name}` but waits for the task to finish
    and returns a ZIP archive containing all output files. It only supports creating single task at a time (`count=1`).

    **Path Parameter:**

    - `name`: Name of the flow from which the task should be created.

    **Query Parameters:**

    - `cleanup`: If `true`(default), the task record and its files will be deleted after completion.
    - `timeout`: Timeout in seconds to wait for the task to complete (default: 600s).

    **Form Data and Headers:**

    - Same as the `/create/{name}` endpoint, but `count` must be 1.

    **Response:**

    - On success, returns a ZIP file (`application/zip`) containing all output files from the task.
    - On failure (e.g., task error, timeout), returns an appropriate HTTP error.
    """
    if data.count > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Synchronous execution does not support count > 1."
        )

    created_tasks = await create_task_logic(request, name, data)
    task_id = created_tasks[0]["task_id"]

    loop = asyncio.get_event_loop()
    end_time = loop.time() + timeout
    task = None

    try:
        # Polling for task completion
        while loop.time() < end_time:
            task = await get_task_async(task_id, request.scope["user_info"].user_id)
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Task disappeared during execution."
                )
            if task["error"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Task failed: {task['error']}"
                )
            if task["progress"] == 100.0:
                break
            await asyncio.sleep(0.2)
        else:  # Loop finished without break, indicating a timeout
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Task execution timed out.")

        # Fetch final task details and prepare results
        task = await get_task_async(task_id, request.scope["user_info"].user_id, fetch_child=True)
        if not task:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Completed task could not be retrieved.")

        all_output_files = get_task_files(task_id, "output")
        files_to_zip = []
        for output_node in task["outputs"]:
            files_to_zip.extend(get_files_for_node(task_id, output_node, all_output_files))

        if not files_to_zip:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=f"No result files found for task=`{task_id}`.",
            )
        return zip_files_as_response(files_to_zip, f"results_{task_id}.zip")
    finally:
        if cleanup:
            task_ids_to_remove = [task_id]
            if task:
                collect_child_task_ids(task, task_ids_to_remove)
            await remove_task_by_id_database(task_ids_to_remove)


@ROUTER.get("/progress")
async def get_tasks_progress(
    request: Request,
    name: str = Query(None, description="Optional name to filter tasks by their name"),
    group_scope: int = Query(1, description="Optional parameter to filter tasks by their group number"),
    only_parent: bool = Query(False, description="Fetch only parent tasks"),
) -> dict[int, TaskDetails]:
    """
    Retrieves the full tasks details information for a specific user.
    Optionally filter tasks by their name or a group number.
    """
    return await get_tasks_async(
        name=name,
        group_scope=group_scope,
        user_id=request.scope["user_info"].user_id,
        fetch_child=True,
        only_parent=only_parent,
    )


@ROUTER.get("/progress-summary")
async def get_tasks_progress_summary(
    request: Request,
    name: str = Query(None, description="Optional name to filter tasks by their name"),
    group_scope: int = Query(1, description="Optional parameter to filter tasks by their group number"),
    only_parent: bool = Query(False, description="Fetch only parent tasks"),
) -> dict[int, TaskDetailsShort]:
    """
    Retrieves summary of the tasks progress details for a specific user.
    Optionally filter tasks by their name or a group number.
    """
    return await get_tasks_short_async(
        name=name,
        group_scope=group_scope,
        user_id=request.scope["user_info"].user_id,
        fetch_child=True,
        only_parent=only_parent,
    )


@ROUTER.get("/progress/{task_id}")
async def get_task_progress(request: Request, task_id: int) -> TaskDetails:
    """
    Retrieves the full task details of a specified task by task ID.
    Access is restricted to the task owner or an administrator.
    """
    r = await get_task_async(task_id, request.scope["user_info"].user_id, fetch_child=True)
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
    r = await get_task_async(task_id, request.scope["user_info"].user_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if r["progress"] == 100.0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task `{task_id}` already finished.")
    if not r["error"] and not force:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task `{task_id}` has no error set.")

    await task_restart_database_async(task_id)
    await remove_task_lock_database(task_id)


@ROUTER.delete(
    "/task",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully removed the specified task and its child tasks"},
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
    Also removes any child tasks associated with the specified task.
    """
    r = await get_task_async(task_id, fetch_child=True)
    if r is None:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    if r["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    task_ids_to_remove = [task_id]
    collect_child_task_ids(r, task_ids_to_remove)
    await remove_task_by_id_database(task_ids_to_remove)


@ROUTER.delete(
    "/clear",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully removed results of all finished parent tasks with the specified name"},
    },
)
async def clear_tasks(
    request: Request,
    name: str = Query(..., description="Name of the task whose results need to be deleted"),
    group_scope: int = Query(
        1, description="Optional group scope to filter tasks only belonging to a specific group. Defaults to 1."
    ),
):
    """
    Removes all finished parent tasks associated with a specific task name,
    scoped to the requesting user and group scope.
    All child tasks associated with the parent tasks will also be deleted.
    """
    r = await get_tasks_async(
        name,
        group_scope,
        True,
        request.scope["user_info"].user_id,
        fetch_child=True,
        only_parent=True,
    )
    task_ids_to_remove = []
    for task_id, task_details in r.items():
        task_ids_to_remove.append(task_id)
        collect_child_task_ids(task_details, task_ids_to_remove)
    await remove_task_by_id_database(task_ids_to_remove)


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
    r = await get_task_async(task_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if r["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    for filename in os.listdir(options.INPUT_DIR):
        if filename == r["input_files"][input_index]["file_name"]:
            return responses.FileResponse(os.path.join(options.INPUT_DIR, filename))
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
        400: {
            "description": "Task not completed",
            "content": {"application/json": {"example": {"detail": "Task `task_id` is not completed yet."}}},
        },
        404: {
            "description": "Task or result file not found",
            "content": {
                "application/json": {"example": {"detail": "Missing result for task=`task_id` and node=`node_id`."}}
            },
        },
    },
)
async def get_task_results(
    request: Request,
    task_id: int = Query(..., description="ID of the task"),
    node_id: int = Query(..., description="ID of the node"),
    batch_index: int = Query(
        0,
        description="Optional index of the node result if the node produced more than one result. "
        "If set to -1, all results for the node are returned as a ZIP archive.",
    ),
):
    """
    Retrieves the result file associated with a specific task and node ID.

    This function searches for output files in the designated output directory that match the task and node identifiers.

    **Parameters:**

    - `task_id` (int): ID of the task.
    - `node_id` (int): ID of the node.
    - `batch_index` (int, optional): Index of the node result if the node produced more than one result.
      - If set to 0 (default), the first result file is returned.
      - If set to a positive integer, the corresponding result file index is returned.
      - If set to -1, all results are returned as a ZIP archive.

    **Returns:**

    - `FileResponse`: The result file or a ZIP archive containing all result files if `batch_index` is -1.
    - `HTTPException`: If the task is not completed or the result file is not found.
    """
    task = await get_task_async(task_id, request.scope["user_info"].user_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if task["progress"] < 100.0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Task `{task_id}` is not completed yet.")

    output_node = next((o for o in task["outputs"] if o["comfy_node_id"] == node_id), None)
    if not output_node:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No such node in the flow for task=`{task_id}`.")

    all_output_files = get_task_files(task_id, "output")
    relevant_files = get_files_for_node(task_id, output_node, all_output_files)
    if not relevant_files:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Missing result for task=`{task_id}` and node=`{node_id}`.",
        )
    if batch_index == -1:
        return zip_files_as_response(relevant_files, f"{task_id}_{node_id}_results.zip")
    if batch_index + 1 > len(relevant_files):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Missing result for task=`{task_id}` and node=`{node_id}`.",
        )
    base_name, extension = os.path.splitext(relevant_files[batch_index][0])
    content_disposition = base_name[:-1] + extension if base_name.endswith("_") else base_name + extension
    return responses.FileResponse(relevant_files[batch_index][1], filename=content_disposition)


@ROUTER.delete(
    "/queue",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully cleared unfinished tasks from the queue"},
    },
)
async def remove_tasks_from_queue(
    request: Request,
    name: str = Query(..., description="Name of the task to clear unfinished tasks from the queue"),
    group_scope: int = Query(
        1, description="Optional group scope to filter tasks only belonging to a specific group. Defaults to 1."
    ),
):
    """
    Clears all unfinished tasks from the queue for a specific task name, scoped to the requesting user and group scope.
    Child tasks are ignored and not removed from the queue.
    """
    await remove_unfinished_tasks_by_name_and_group(name, request.scope["user_info"].user_id, group_scope)


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
    if await get_task_async(task_id, request.scope["user_info"].user_id) is None:
        raise HTTPException(status_code=404, detail=f"Task `{task_id}` was not found.")
    await remove_unfinished_task_by_id(task_id)


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
    task = await get_incomplete_task_without_error_database(
        request.scope["user_info"].user_id, worker_details, tasks_names, last_task_name, user_id
    )
    if not task:
        return responses.Response(status_code=status.HTTP_204_NO_CONTENT)
    return task


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
    execution_details: ExecutionDetails | None = Body(None),
):
    """
    Updates the progress of a specific task identified by `task_id`. This endpoint checks if the task exists
    and if the requester is authorized to update its progress. If the task is not found or unauthorized,
    a 404 HTTP error is raised, and `worker` should stop and consider the task canceled.
    """
    r = await get_task_async(task_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    user_info = request.scope["user_info"]
    if r["user_id"] != user_info.user_id and not user_info.is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if not await update_task_progress_database(
        task_id, progress, error, execution_time, user_info.user_id, worker_details, execution_details
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update task progress.")
    if r["webhook_url"]:
        b_tasks.add_task(
            webhook_task_progress, r["webhook_url"], r["webhook_headers"], task_id, progress, execution_time, error
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
    task_details = await get_task_async(task_id)
    if task_details is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if task_details["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    for task_output in task_details["outputs"]:
        task_file_prefix = f"{task_id}_{task_output['comfy_node_id']}_"
        relevant_files = [file_info for file_info in files if file_info.filename.startswith(task_file_prefix)]
        if not relevant_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No results found for: {task_file_prefix}",
            )
        file_size = 0
        batch_size = 0
        for i in relevant_files:
            file_size += i.size
            batch_size += 1
            try:
                file_path = Path(options.OUTPUT_DIR).joinpath("visionatrix").joinpath(i.filename)
                with builtins.open(file_path, mode="wb") as out_file:
                    shutil.copyfileobj(i.file, out_file)
            finally:
                i.file.close()
        task_output["file_size"] = file_size
        task_output["batch_size"] = batch_size
    await update_task_outputs_async(task_id, task_details["outputs"])


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
    r = await get_task_async(task_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    if r["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")
    await remove_task_lock_database(task_id)


@ROUTER.put(
    "/update",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully updated the task"},
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "examples": {
                        "Task started": {
                            "summary": "Task already started",
                            "value": {"detail": "Task `{task_id}` cannot be updated because it has already started."},
                        },
                        "Invalid priority": {
                            "summary": "Invalid priority",
                            "value": {"detail": "Priority cannot be greater than 15."},
                        },
                        "No fields": {
                            "summary": "No fields to update",
                            "value": {"detail": "No valid fields to update."},
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
async def update_task_info(
    request: Request,
    task_id: int = Query(..., description="ID of the task to update"),
    update_data: TaskUpdateRequest = Body(..., description="Fields to update"),
):
    """
    Updates the information of a task specified by `task_id`. Only tasks that have not yet started (progress == 0.0)
    can be updated. Currently, only the `priority` field can be updated.

    The `priority` parameter must not exceed 15.

    Access is restricted to the task owner or an administrator.
    """
    task = await get_task_async(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")

    if task["user_id"] != request.scope["user_info"].user_id and not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task `{task_id}` was not found.")

    if task["progress"] != 0.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task `{task_id}` cannot be updated because it has already started.",
        )

    update_fields = update_data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update.")

    if "priority" in update_fields and update_fields["priority"] > 15:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Priority cannot be greater than 15.")

    update_fields["priority"] = ((task["group_scope"] - 1) << 4) + update_fields["priority"]
    if not await update_task_info_database_async(task_id, update_fields):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update task `{task_id}`.")
