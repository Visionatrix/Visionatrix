import logging
import typing

import httpx
from fastapi import HTTPException, UploadFile, status

from .. import options
from ..db_queries import get_setting
from ..db_queries_async import get_setting_async
from ..flows import (
    Flow,
    flow_prepare_output_params,
    get_nodes_for_translate,
    prepare_flow_comfy,
)
from ..prompt_translation import (
    translate_prompt_with_gemini,
    translate_prompt_with_gemini_async,
    translate_prompt_with_ollama,
    translate_prompt_with_ollama_async,
)
from ..pydantic_models import TranslatePromptRequest, UserInfo
from ..tasks_engine import create_new_task, put_task_in_queue, remove_task_files
from ..tasks_engine_async import create_new_task_async, put_task_in_queue_async

LOGGER = logging.getLogger("visionatrix")
VALIDATE_PROMPT: typing.Callable[[dict], tuple[bool, dict, list, list]] | None = None


async def task_run(
    name: str,
    input_params: dict,
    translated_input_params: dict,
    in_files: list[UploadFile | dict],
    flow: Flow,
    flow_comfy: dict,
    user_info: UserInfo,
    webhook_url: str | None,
    webhook_headers: dict | None,
    child_task: bool,
    group_scope: int,
    priority: int,
):
    if options.VIX_MODE == "SERVER":
        task_details = await create_new_task_async(name, input_params, user_info)
    else:
        task_details = create_new_task(name, input_params, user_info)
    input_params_copy = input_params.copy()
    for i, v in translated_input_params.items():
        input_params_copy[i] = v
    try:
        flow_comfy = prepare_flow_comfy(flow, flow_comfy, input_params_copy, in_files, task_details)
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
    task_details["group_scope"] = group_scope
    task_details["priority"] = ((group_scope - 1) << 4) + priority
    if translated_input_params:
        task_details["translated_input_params"] = translated_input_params
    flow_prepare_output_params(flow_validation[2], task_details["task_id"], task_details, flow_comfy)
    if options.VIX_MODE == "SERVER":
        await put_task_in_queue_async(task_details)
    else:
        put_task_in_queue(task_details)
    return task_details


async def get_translated_input_params(
    translate: bool, flow: Flow, input_params_dict: dict, flow_comfy: dict, user_id: str, is_user_admin: bool
):
    translated_input_params_dict = {}
    if translate and flow.is_translations_supported:
        nodes_for_translate = get_nodes_for_translate(input_params_dict, flow_comfy)
        if not nodes_for_translate:
            return translated_input_params_dict
        if options.VIX_MODE == "SERVER":
            translations_provider = await get_setting_async(user_id, "translations_provider", is_user_admin)
        else:
            translations_provider = get_setting(user_id, "translations_provider", is_user_admin)
        if translations_provider:
            if translations_provider not in ("ollama", "gemini"):
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail=f"Unknown translation provider: {translations_provider}",
                )
            for node_to_translate in nodes_for_translate:
                tr_req = TranslatePromptRequest(prompt=node_to_translate["input_param_value"])
                if node_to_translate["llm_prompt"]:
                    tr_req.system_prompt = node_to_translate["llm_prompt"]
                try:
                    if translations_provider == "ollama":
                        if options.VIX_MODE == "SERVER":
                            r = await translate_prompt_with_ollama_async(user_id, is_user_admin, tr_req)
                        else:
                            r = translate_prompt_with_ollama(user_id, is_user_admin, tr_req)
                    else:
                        if options.VIX_MODE == "SERVER":
                            r = await translate_prompt_with_gemini_async(user_id, is_user_admin, tr_req)
                        else:
                            r = translate_prompt_with_gemini(user_id, is_user_admin, tr_req)
                except Exception as e:
                    LOGGER.exception(
                        "Exception during prompt translation using `%s` for user `%s`", translations_provider, user_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
