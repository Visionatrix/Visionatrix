import builtins
import json
import logging
import typing
from datetime import datetime, timedelta, timezone
from io import BytesIO
from zipfile import ZipFile

import httpx
from fastapi import HTTPException, Request, responses, status
from starlette.datastructures import UploadFile as StarletteUploadFile

from .. import etc, models_map
from ..db_queries import (
    get_all_global_settings_for_task_execution,
    get_installed_models,
    get_setting,
    get_worker_details,
    is_custom_worker_free,
)
from ..flows import (
    SUPPORTED_FILE_TYPES_INPUTS,
    SUPPORTED_TEXT_TYPES_INPUTS,
    Flow,
    flow_prepare_output_params,
    get_installed_flow,
    get_nodes_for_translate,
    prepare_flow_comfy,
)
from ..prompt_translation import (
    translate_prompt_with_gemini,
    translate_prompt_with_ollama,
)
from ..pydantic_models import (
    TaskCreationWithFullParams,
    TranslatePromptRequest,
    UserInfo,
)
from ..surprise_me import surprise_me
from ..tasks_engine import remove_task_files
from ..tasks_engine_async import (
    create_new_task_async,
    get_task_async,
    put_task_in_queue_async,
)

LOGGER = logging.getLogger("visionatrix")
VALIDATE_PROMPT: typing.Callable[[str, dict], typing.Awaitable[tuple[bool, dict, list, list]]] | None = None


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
    extra_flags: dict,
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

    flow_validation: [bool, dict, list, list] = await VALIDATE_PROMPT("vix-" + str(task_details["task_id"]), flow_comfy)
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


async def get_task_creation_extra_flags(request: Request, is_user_admin: bool) -> [dict, str | None]:
    extra_flags = await get_all_global_settings_for_task_execution()
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
    return extra_flags, custom_worker


async def preprocess_federation_task(extra_flags: dict, custom_worker: str | None) -> None:
    if not extra_flags.get("federated_task"):
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
    if not await is_custom_worker_free(custom_worker):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Worker has unfinished tasks.") from None


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


async def create_task_logic(
    request: Request,
    name: str,
    data: TaskCreationWithFullParams,
) -> list[dict]:
    """Internal logic to create one or more tasks, returns a list of task_details dicts."""
    user_id = request.scope["user_info"].user_id
    is_user_admin = request.scope["user_info"].is_admin
    extra_flags, custom_worker = await get_task_creation_extra_flags(request, is_user_admin)
    await preprocess_federation_task(extra_flags, custom_worker)

    flow_comfy = {}
    flow = await get_installed_flow(name, flow_comfy)
    if not flow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Flow `{name}` is not installed.") from None

    form_data = await request.form()

    in_text_params: dict[str, int | float | str] = {}
    in_files_params = {}
    flow_input_params = {}
    for input_param in flow.input_params:
        flow_input_params[input_param["name"]] = input_param

    standard_params = list(TaskCreationWithFullParams.model_fields.keys())
    surprise_me_active = False
    for key in form_data:
        if flow.is_seed_supported and key == "seed":
            in_text_params["seed"] = int(form_data.get(key))
            continue
        if key == "surprise_me" and flow.is_surprise_me_supported and form_data["surprise_me"] == "1":
            surprise_me_active = True
            continue
        if key in standard_params:
            continue
        if key not in flow_input_params:
            LOGGER.warning("Unexpected parameter '%s' for '%s' task creation, ignoring.", key, name)
            continue
        value = form_data.get(key)
        if flow_input_params[key]["type"] in SUPPORTED_TEXT_TYPES_INPUTS:
            in_text_params[key] = value
            continue
        if flow_input_params[key]["type"] not in SUPPORTED_FILE_TYPES_INPUTS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported input type '{flow_input_params[key]['type']}' for {key} parameter.",
            ) from None
        if isinstance(value, str):
            await process_string_value(request, user_id, key, value, in_files_params)
        elif isinstance(value, StarletteUploadFile):
            in_files_params[key] = value
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=f"Unsupported input file type: {type(value)}"
            ) from None

    translated_in_text_params = await get_translated_input_params(
        bool(data.translate), flow, in_text_params, flow_comfy, user_id, is_user_admin
    )

    if "seed" in in_text_params:
        in_text_params_list = [dict(in_text_params, seed=in_text_params["seed"] + i) for i in range(data.count)]
    else:
        in_text_params_list = [in_text_params.copy() for _ in range(data.count)]
    translated_in_text_params_list = [translated_in_text_params.copy() for _ in range(data.count)]

    if surprise_me_active:
        if "prompt" in translated_in_text_params:
            ai_generated_prompts: list = await surprise_me(
                user_id, is_user_admin, translated_in_text_params["prompt"], count=data.count
            )
            for i in range(data.count):
                translated_in_text_params_list[i]["prompt"] = ai_generated_prompts[i]
        else:
            ai_generated_prompts: list = await surprise_me(
                user_id, is_user_admin, in_text_params.get("prompt", ""), count=data.count
            )
            for i in range(data.count):
                in_text_params_list[i]["prompt"] = ai_generated_prompts[i]

    created_tasks = []
    webhook_headers_dict = json.loads(data.webhook_headers) if data.webhook_headers else None
    for i in range(data.count):
        task_details = await task_run(
            name,
            in_text_params_list[i],
            translated_in_text_params_list[i],
            in_files_params,
            flow,
            flow_comfy,
            request.scope["user_info"],
            data.webhook_url if data.webhook_url else None,
            webhook_headers_dict,
            bool(data.child_task),
            data.group_scope,
            data.priority,
            extra_flags,
            custom_worker,
        )
        created_tasks.append(task_details)

    return created_tasks


def get_files_for_node(
    task_id: int, output_node: dict, all_output_files: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    """Filters a list of all output files to find those relevant to a specific output node."""
    node_id = output_node["comfy_node_id"]
    result_prefix = f"{task_id}_{node_id}_"
    relevant_files = [f_info for f_info in all_output_files if f_info[0].startswith(result_prefix)]
    type_extensions = {
        "image": etc.IMAGE_EXTENSIONS,
        "image-animated": etc.IMAGE_ANIMATED_EXTENSIONS,
        "video": etc.VIDEO_EXTENSIONS,
        "audio": etc.AUDIO_EXTENSIONS,
        "text": etc.TEXT_EXTENSIONS,
        "3d-model": etc.MODEL3D_EXTENSION,
    }
    extensions_to_check = type_extensions.get(output_node["type"])
    if extensions_to_check:
        relevant_files = [f for f in relevant_files if any(f[0].endswith(ext) for ext in extensions_to_check)]
    return relevant_files


def zip_files_as_response(files_to_zip: list[tuple[str, str]], archive_name: str) -> responses.Response:
    """Zips a list of files into a FastAPI response."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zip_file:
        for file_name, file_path in files_to_zip:
            with builtins.open(file_path, "rb") as f:
                zip_file.writestr(file_name, f.read())

    zip_buffer.seek(0)

    return responses.Response(
        content=zip_buffer.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={archive_name}"},
    )
