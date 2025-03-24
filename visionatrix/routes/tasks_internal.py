import json
import logging
import typing
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException, Request, status
from starlette.datastructures import UploadFile as StarletteUploadFile

from .. import models_map
from ..db_queries import get_installed_models, get_setting, get_worker_details
from ..flows import (
    Flow,
    flow_prepare_output_params,
    get_nodes_for_translate,
    prepare_flow_comfy,
)
from ..prompt_translation import (
    translate_prompt_with_gemini,
    translate_prompt_with_ollama,
)
from ..pydantic_models import TranslatePromptRequest, UserInfo
from ..tasks_engine import remove_task_files
from ..tasks_engine_async import (
    create_new_task_async,
    get_task_async,
    put_task_in_queue_async,
)

LOGGER = logging.getLogger("visionatrix")
VALIDATE_PROMPT: typing.Callable[[dict], tuple[bool, dict, list, list]] | None = None


async def task_run(
    name: str,
    input_params: dict,
    translated_input_params: dict,
    in_files: dict[str, StarletteUploadFile | dict],
    flow: Flow,
    flow_comfy: dict,
    user_info: UserInfo,
    webhook_url: str | None,
    webhook_headers: dict | None,
    child_task: bool,
    group_scope: int,
    priority: int,
    extra_flags: dict | None,
    custom_worker: str | None,
):
    task_details = await create_new_task_async(name, input_params, user_info)
    models_map.process_flow_models(flow_comfy, await get_installed_models())
    input_params_copy = input_params.copy()
    for i, v in translated_input_params.items():
        input_params_copy[i] = v
    try:
        flow_comfy = prepare_flow_comfy(flow, flow_comfy, input_params_copy, in_files, task_details)
    except RuntimeError as e:
        remove_task_files(task_details["task_id"], ["input"])
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from None

    flow_validation: [bool, dict, list, list] = VALIDATE_PROMPT(flow_comfy)
    if not flow_validation[0]:
        remove_task_files(task_details["task_id"], ["input"])
        LOGGER.error("Flow validation error: %s\n%s", flow_validation[1], flow_validation[3])
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Bad Flow: `{flow_validation[1]}`") from None
    task_details["flow_comfy"] = flow_comfy
    task_details["webhook_url"] = webhook_url
    task_details["webhook_headers"] = webhook_headers
    if child_task:
        if not in_files:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="No input file provided. Use the parent task's node ID.",
            ) from None
        in_file = next(iter(in_files.values()))
        if not isinstance(in_file, dict):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Invalid input file. Use the parent task's node ID.",
            ) from None
        task_details["parent_task_id"] = in_file["task_id"]
        task_details["parent_task_node_id"] = in_file["node_id"]
    task_details["group_scope"] = group_scope
    task_details["priority"] = ((group_scope - 1) << 4) + priority
    if translated_input_params:
        task_details["translated_input_params"] = translated_input_params
    if extra_flags:
        task_details["extra_flags"] = extra_flags
    if custom_worker:
        task_details["custom_worker"] = custom_worker
    if flow.hidden or extra_flags.get("federated_task"):
        task_details["hidden"] = True
    flow_prepare_output_params(flow_validation[2], task_details["task_id"], task_details, flow_comfy)
    await put_task_in_queue_async(task_details)
    return task_details


async def get_translated_input_params(
    translate: bool, flow: Flow, input_params_dict: dict, flow_comfy: dict, user_id: str, is_user_admin: bool
):
    translated_input_params_dict = {}
    if translate and flow.is_translations_supported:
        nodes_for_translate = get_nodes_for_translate(input_params_dict, flow_comfy)
        if not nodes_for_translate:
            return translated_input_params_dict
        translations_provider = await get_setting(user_id, "translations_provider", is_user_admin)
        if translations_provider:
            if translations_provider not in ("ollama", "gemini"):
                raise HTTPException(
                    status.HTTP_501_NOT_IMPLEMENTED,
                    detail=f"Unknown translation provider: {translations_provider}",
                )
            for node_to_translate in nodes_for_translate:
                tr_req = TranslatePromptRequest(prompt=node_to_translate["input_param_value"])
                if node_to_translate["llm_prompt"]:
                    tr_req.system_prompt = node_to_translate["llm_prompt"]
                try:
                    if translations_provider == "ollama":
                        r = await translate_prompt_with_ollama(user_id, is_user_admin, tr_req)
                    else:
                        r = await translate_prompt_with_gemini(user_id, is_user_admin, tr_req)
                except Exception as e:
                    LOGGER.exception(
                        "Exception during prompt translation using `%s` for user `%s`", translations_provider, user_id
                    )
                    raise HTTPException(
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Can't translate the prompt: provider={translations_provider}, "
                        f"user_id={user_id}, prompt=`{tr_req.prompt}`: {e}",
                    ) from None
                translated_input_params_dict[node_to_translate["input_param_id"]] = r.result
    return translated_input_params_dict


async def webhook_task_progress(
    url: str, headers: dict | None, task_id: int, progress: float, execution_time: float, error: str
) -> None:
    try:
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
    except httpx.RequestError as e:
        LOGGER.exception("Exception during calling webhook %s, progress=%s: %s", url, progress, e)


async def process_remote_input_url(request: Request, input_file_info: dict[str, str | bytes]) -> None:
    remote_url_type = input_file_info.get("type")
    if remote_url_type != "nextcloud":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown type({remote_url_type} for `remote_url` parameter",
        ) from None
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        input_file = await client.get(input_file_info["remote_url"], cookies=request.cookies)
        input_file_info["file_content"] = input_file.content


def get_task_creation_extra_flags(request: Request, is_user_admin: bool) -> [dict | None, str | None]:
    extra_flags = {}
    custom_worker = None
    if is_user_admin:
        custom_worker = request.headers.get("X-WORKER-ID")
        if request.headers.get("X-WORKER-UNLOAD-MODELS") == "1":
            extra_flags["unload_models"] = True
        if request.headers.get("X-WORKER-EXECUTION-PROFILER") == "1":
            extra_flags["profiler_execution"] = True
        if request.headers.get("X-FEDERATED-TASK") == "1":
            if not custom_worker:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing `X-WORKER-ID` header.") from None
            extra_flags["federated_task"] = True
    if not extra_flags:
        extra_flags = None
    return extra_flags, custom_worker


async def preprocess_federation_task(extra_flags: dict | None, custom_worker: str | None) -> None:
    if not extra_flags or not extra_flags.get("federated_task"):
        return
    worker = await get_worker_details(None, custom_worker)
    if not worker:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No such worker available.") from None
    if worker.empty_task_requests_count < 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Worker is busy.") from None
    if worker.federated_instance_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Worker is a federated one.") from None
    if worker.last_seen.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc) - timedelta(seconds=15.0):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Worker is offline.") from None


async def process_string_value(request: Request, user_id: str, key: str, value: str, in_files_params: dict) -> None:
    try:
        input_file_info = json.loads(value)
    except json.JSONDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Invalid file input:{value}") from None
    if "remote_url" in input_file_info:
        await process_remote_input_url(request, input_file_info)
    elif "task_id" in input_file_info:
        task_info = await get_task_async(int(input_file_info["task_id"]), user_id)
        if not task_info:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=f"Missing task with id={input_file_info['task_id']}"
            ) from None
        input_file_info["task_info"] = task_info
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Missing `task_id` or `remote_url` parameter."
        ) from None
    in_files_params[key] = input_file_info
