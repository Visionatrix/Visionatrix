import asyncio
import builtins
import io
import json
import logging
import os
import random
import shutil
import threading
import time
import typing
import zipfile
from base64 import b64decode
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

import httpx
from packaging.version import Version, parse
from starlette.datastructures import UploadFile as StarletteUploadFile

from . import (
    _version,
    comfyui_class_info,
    db_queries,
    events,
    options,
)
from .comfyui_wrapper import get_node_class_mappings
from .etc import is_english
from .flows_loras import (
    add_loras_inputs,
    flow_add_model,
    flow_remove_model,
    get_flow_lora_connect_points,
    get_ui_input_attribute,
    insert_lora_in_comfy_flow,
    remove_all_consecutive_loras_for_node,
)
from .models import fill_flows_model_installed_field, install_model
from .models_map import process_flow_models
from .nodes_helpers import get_node_value, set_node_value
from .pydantic_models import Flow, FlowCloneRequest, LoraConnectionPoint, WorkerDetails

LOGGER = logging.getLogger("visionatrix")

SECONDS_TO_CACHE_AVAILABLE_FLOWS = 3 * 60
LAST_GOOD_AVAILABLE_FLOWS = {
    "update_time": 0.0,  # single timestamp for "all available flows" refresh
    "flows": {},  # final merged flows across all URLs
    "flows_comfy": {},  # final merged flows_comfy across all URLs
    "per_storage": {},  # per-URL dict => { url: {...} }
}
LOCK_AVAILABLE_FLOWS = threading.Lock()
LOCK_AVAILABLE_FLOWS_UPDATING = threading.Lock()
SECONDS_TO_CACHE_INSTALLED_FLOWS = 10

LAST_GOOD_INSTALLED_FLOWS = {
    "update_time": 0.0,
    "flows": {},
    "flows_comfy": {},
}
LOCK_INSTALLED_FLOWS = threading.Lock()
LOCK_INSTALLED_FLOWS_UPDATING = threading.Lock()

SUPPORTED_OUTPUTS = {
    "SaveImage": "image",
    "SaveAnimatedWEBP": "image-animated",
    "VHS_VideoCombine": "video",
    "SaveWEBM": "video",
    "SaveAudio": "audio",
    "SaveText|pysssss": "text",
    "SaveGLB": "3d-model",
}

SUPPORTED_TEXT_TYPES_INPUTS = ["text", "number", "list", "bool", "range", "range_scale"]
SUPPORTED_FILE_TYPES_INPUTS = ["image", "image-mask", "video"]


async def get_available_flows(flows_comfy: dict[str, dict] | None = None) -> dict[str, Flow]:
    if flows_comfy is None:
        flows_comfy = {}
    else:
        flows_comfy.clear()
    current_time = time.time()
    with LOCK_AVAILABLE_FLOWS:
        if current_time < LAST_GOOD_AVAILABLE_FLOWS["update_time"] + SECONDS_TO_CACHE_AVAILABLE_FLOWS:
            flows_comfy.update(LAST_GOOD_AVAILABLE_FLOWS["flows_comfy"])
            return deepcopy(LAST_GOOD_AVAILABLE_FLOWS["flows"])

    if LOCK_AVAILABLE_FLOWS_UPDATING.acquire(blocking=False):  # pylint: disable=consider-using-with
        try:
            updated_flows, updated_flows_comfy, new_per_storage = await __fetch_and_merge_all_flows(
                LAST_GOOD_AVAILABLE_FLOWS.get("per_storage", {})
            )
            with LOCK_AVAILABLE_FLOWS:
                LAST_GOOD_AVAILABLE_FLOWS["update_time"] = time.time()
                LAST_GOOD_AVAILABLE_FLOWS["flows"] = updated_flows
                LAST_GOOD_AVAILABLE_FLOWS["flows_comfy"] = updated_flows_comfy
                LAST_GOOD_AVAILABLE_FLOWS["per_storage"] = new_per_storage
            flows_comfy.update(updated_flows_comfy)
            return deepcopy(updated_flows)
        finally:
            LOCK_AVAILABLE_FLOWS_UPDATING.release()

    with LOCK_AVAILABLE_FLOWS:
        flows_comfy.update(LAST_GOOD_AVAILABLE_FLOWS["flows_comfy"])
        return deepcopy(LAST_GOOD_AVAILABLE_FLOWS["flows"])


async def __fetch_and_merge_all_flows(
    old_per_storage: dict[str, dict],
) -> tuple[dict[str, Flow], dict[str, dict], dict[str, dict]]:
    """Fetch from each URL in options.FLOWS_URL. We'll keep per-URL data in
    LAST_GOOD_AVAILABLE_FLOWS["per_storage"][url], so if a server returns
    304 or error, we preserve the existing data for that URL.
    Finally, we merge all per-URL data into a single big 'combined_flows'.
    """

    flows_storage_urls = [url.strip() for url in options.FLOWS_URL.split(";") if url.strip()]
    if not flows_storage_urls:
        LOGGER.warning("'FLOWS_URL' is empty. Unable to get available flows.")
        return {}, {}, old_per_storage

    new_per_storage = deepcopy(old_per_storage)
    for url in flows_storage_urls:
        per_url_data = new_per_storage.get(url, {"etag": "", "flows": {}, "flows_comfy": {}})
        flows, flows_comfy_single, fresh_etag = await fetch_flows_from_url_or_path(url, per_url_data["etag"])
        if flows is None:
            LOGGER.debug("No new data from '%s' (304 or error), preserving old data", url)
            continue
        LOGGER.debug("Got new data from %s", url)
        per_url_data["etag"] = fresh_etag
        per_url_data["flows"] = flows
        per_url_data["flows_comfy"] = flows_comfy_single
        new_per_storage[url] = per_url_data

    combined_flows: dict[str, Flow] = {}
    combined_flows_comfy: dict[str, dict] = {}
    for data_dict in new_per_storage.values():
        flows_comfy_dict = data_dict["flows_comfy"]
        for flow_name, flow_obj in data_dict["flows"].items():
            if flow_name not in combined_flows or parse(flow_obj.version) > parse(combined_flows[flow_name].version):
                combined_flows[flow_name] = flow_obj
                combined_flows_comfy[flow_name] = flows_comfy_dict[flow_name]
    return combined_flows, combined_flows_comfy, new_per_storage


async def fetch_flows_from_url_or_path(flows_storage_url: str, etag: str):
    r_flows = {}
    r_flows_comfy = {}
    if flows_storage_url.endswith("/"):
        vix_version = Version(_version.__version__)
        if vix_version.is_devrelease:
            flows_storage_url += "flows.zip"
        else:
            flows_storage_url += f"flows-{vix_version.major}.{vix_version.minor}.zip"
    parsed_url = urlparse(flows_storage_url)
    if parsed_url.scheme in ("http", "https", "ftp", "ftps"):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(flows_storage_url, headers={"If-None-Match": etag})
        except httpx.TransportError as e:
            LOGGER.error("Request to get flows failed with: %s", e)
            return None, None, etag
        if r.status_code == 304:
            return None, None, etag
        if r.status_code != 200:
            LOGGER.error("Request to get flows returned: %s", r.status_code)
            return None, None, etag
        flows_content = r.content
        flows_content_etag = r.headers.get("etag", etag)
    else:
        try:
            with builtins.open(flows_storage_url, mode="rb") as flows_archive:
                flows_content = flows_archive.read()
            flows_content_etag = etag
        except Exception as e:
            LOGGER.error("Failed to read flows archive at %s: %s", flows_storage_url, e)
            return None, None, etag

    flow_comfy_path = None
    try:
        with zipfile.ZipFile(io.BytesIO(flows_content)) as zip_file:
            for flow_comfy_path in {name for name in zip_file.namelist() if name.endswith(".json")}:
                with zip_file.open(flow_comfy_path) as flow_comfy_file:
                    _flow_comfy = json.loads(flow_comfy_file.read())
                    _flow = get_vix_flow(_flow_comfy)
                    _flow_name = _flow.name
                    r_flows[_flow_name] = _flow
                    r_flows_comfy[_flow_name] = _flow_comfy
    except Exception as e:
        LOGGER.exception("Failed to parse flows from %s(%s): %s", flows_storage_url, flow_comfy_path, e)
        return None, None, etag

    return r_flows, r_flows_comfy, flows_content_etag


async def get_not_installed_flows(flows_comfy: dict[str, dict] | None = None) -> dict[str, Flow]:
    installed_flows_ids = list(await get_installed_flows())
    avail_flows_comfy = {}
    avail_flows = await get_available_flows(avail_flows_comfy)
    flows = {}
    for i, v in avail_flows.items():
        if i not in installed_flows_ids:
            flows[i] = v
            if flows_comfy is not None:
                flows_comfy[i] = avail_flows_comfy[i]
    return flows


async def get_installed_flows(flows_comfy: dict[str, dict] | None = None) -> dict[str, Flow]:
    if flows_comfy is None:
        flows_comfy = {}
    else:
        flows_comfy.clear()
    current_time = time.time()

    with LOCK_INSTALLED_FLOWS:
        if current_time < LAST_GOOD_INSTALLED_FLOWS["update_time"] + SECONDS_TO_CACHE_INSTALLED_FLOWS:
            flows_comfy.update(LAST_GOOD_INSTALLED_FLOWS["flows_comfy"])
            return deepcopy(LAST_GOOD_INSTALLED_FLOWS["flows"])

    if LOCK_INSTALLED_FLOWS_UPDATING.acquire(blocking=False):  # pylint: disable=consider-using-with
        try:
            updated_flows, updated_flows_comfy = await __get_installed_flows()
            with LOCK_INSTALLED_FLOWS:
                LAST_GOOD_INSTALLED_FLOWS["update_time"] = time.time()
                LAST_GOOD_INSTALLED_FLOWS["flows"] = updated_flows
                LAST_GOOD_INSTALLED_FLOWS["flows_comfy"] = updated_flows_comfy
            flows_comfy.update(updated_flows_comfy)
            return deepcopy(updated_flows)
        finally:
            LOCK_INSTALLED_FLOWS_UPDATING.release()

    with LOCK_INSTALLED_FLOWS:
        flows_comfy.update(LAST_GOOD_INSTALLED_FLOWS["flows_comfy"])
        return deepcopy(LAST_GOOD_INSTALLED_FLOWS["flows"])


async def __get_installed_flows() -> [dict[str, Flow], dict[str, dict]]:
    available_flows = await get_available_flows({})
    public_flows_names = list(available_flows)
    installed_flows = await db_queries.get_installed_flows()
    new_flows = {}
    new_flows_comfy = {}
    for installed_flow in installed_flows:
        installed_flow.flow = get_vix_flow(installed_flow.flow_comfy)
        if installed_flow.name not in public_flows_names:
            installed_flow.flow.private = True
        fresh_flow_info = available_flows.get(installed_flow.name)
        if fresh_flow_info and parse(installed_flow.flow.version) < parse(fresh_flow_info.version):
            installed_flow.flow.new_version_available = fresh_flow_info.version
        new_flows[installed_flow.name] = installed_flow.flow
        new_flows_comfy[installed_flow.name] = installed_flow.flow_comfy
    return new_flows, new_flows_comfy


async def get_installed_flow(flow_name: str, flow_comfy: dict[str, dict]) -> Flow | None:
    flows_comfy = {}
    flow = (await get_installed_flows(flows_comfy)).get(flow_name)
    if flow:
        flow_comfy.clear()
        flow_comfy.update(flows_comfy[flow_name])
    return flow


async def install_custom_flow(flow: Flow, flow_comfy: dict) -> bool:
    await db_queries.delete_flow_progress_install(flow.name)
    await db_queries.add_flow_progress_install(flow.name, flow_comfy, [i.name for i in flow.models])

    auth_tokens = {"huggingface_auth_token": "", "civitai_auth_token": ""}
    async with httpx.AsyncClient(timeout=float(options.WORKER_NET_TIMEOUT)) as client:
        for token_env, token_key in [
            ("HF_AUTH_TOKEN", "huggingface_auth_token"),
            ("CA_AUTH_TOKEN", "civitai_auth_token"),
        ]:
            if token_env in os.environ:
                auth_tokens[token_key] = os.environ[token_env]
            elif options.VIX_MODE == "WORKER" and options.VIX_SERVER:
                try:
                    r = await client.get(
                        options.VIX_SERVER.rstrip("/") + "/setting",
                        params={"key": token_key},
                        auth=options.worker_auth(),
                    )
                    if not httpx.codes.is_error(r.status_code):
                        auth_tokens[token_key] = r.text.strip()
                except Exception as e:
                    LOGGER.error("Error fetching `%s`: %s", token_key, str(e))
            else:
                auth_tokens[token_key] = await db_queries.get_global_setting(token_key, True)

    semaphore = asyncio.Semaphore(2)

    async def _install_model_with_semaphore(model_to_install):
        async with semaphore:
            return await install_model(
                model_to_install,
                flow.name,
                (auth_tokens["huggingface_auth_token"], auth_tokens["civitai_auth_token"]),
            )

    tasks = [asyncio.create_task(_install_model_with_semaphore(model)) for model in flow.models]

    install_models_results = []
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                if isinstance(result, KeyboardInterrupt):
                    raise result
                LOGGER.exception("Error during models installation: %s", result)
                install_models_results.append(False)
            else:
                install_models_results.append(result)

    except KeyboardInterrupt:
        LOGGER.warning("Flow installation interrupted by user.")
        for task in tasks:
            if not task.done():
                task.cancel()
        events.EXIT_EVENT.set()
        events.EXIT_EVENT_ASYNC.set()
        await db_queries.set_flow_progress_install_error(flow.name, "Installation canceled by user")
        return False
    except Exception as e:
        LOGGER.exception("Unexpected error during flow installation: %s", e)
        await db_queries.set_flow_progress_install_error(flow.name, f"Unexpected error: {e}")
        return False

    if not all(install_models_results):
        LOGGER.info("Installation of `%s` was unsuccessful", flow.name)
        return False

    if not await db_queries.mark_flow_as_installed(flow.name):
        return False
    LOGGER.info("Installation of `%s` flow completed", flow.name)

    with LOCK_INSTALLED_FLOWS:
        LAST_GOOD_INSTALLED_FLOWS["flows"][flow.name] = flow
        LAST_GOOD_INSTALLED_FLOWS["flows_comfy"][flow.name] = flow_comfy
    return True


async def uninstall_flow(flow_name: str) -> None:
    with LOCK_INSTALLED_FLOWS:
        if await db_queries.delete_flow_progress_install(flow_name):
            LAST_GOOD_INSTALLED_FLOWS["flows"].pop(flow_name, None)
            LAST_GOOD_INSTALLED_FLOWS["flows_comfy"].pop(flow_name, None)


def prepare_flow_comfy(
    flow: Flow,
    flow_comfy: dict,
    in_texts_params: dict,
    in_files_params: dict[str, StarletteUploadFile | dict],
    task_details: dict,
) -> dict:
    r = deepcopy(flow_comfy)
    for i in [i for i in flow.input_params if i["type"] in SUPPORTED_TEXT_TYPES_INPUTS]:
        v = prepare_flow_comfy_get_input_value(in_texts_params, i)
        if v is None:
            continue
        for k, input_path in i["comfy_node_id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad workflow, node with id=`{k}` can not be found.")
            set_node_value(node, input_path, v)
    process_seed_value(flow, in_texts_params, r)
    prepare_flow_comfy_files_params(flow, in_files_params, task_details["task_id"], task_details, r)
    return r


def prepare_flow_comfy_get_input_value(in_texts_params: dict, i: dict) -> typing.Any:
    v = in_texts_params.get(i["name"], None)
    if v is None:
        if "default" in i:
            v = i["default"]
        elif not i.get("optional", False):
            raise RuntimeError(f"Missing `{i['name']}` parameter.")
        else:
            return None
    if i["type"] == "list":  # for `list` type we need associated values
        v = i["options"][v]
    elif i["type"] == "bool":
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in {"true", "1", "yes", "y", "on"}:
                v = True
            elif v_lower in {"false", "0", "no", "n", "off"}:
                v = False
            else:
                raise ValueError(f"Invalid boolean value: {v}")
        else:
            v = bool(v)
    return v


def prepare_flow_comfy_files_params(
    flow: Flow, in_files_params: dict[str, StarletteUploadFile | dict], task_id: int, task_details: dict, r: dict
) -> None:
    files_params = [i for i in flow.input_params if i["type"] in SUPPORTED_FILE_TYPES_INPUTS]
    flow_input_file_params = {}
    for file_param in files_params:
        file_param_name = file_param["name"]
        flow_input_file_params[file_param_name] = file_param
        if file_param_name not in in_files_params and not file_param.get("optional", False):
            raise RuntimeError(f"The parameter '{file_param_name}' is required, but missing.")
    for param_name, v in in_files_params.items():
        if isinstance(v, dict):
            if "input_index" in v:
                input_file = str(
                    os.path.join(options.INPUT_DIR, v["task_info"]["input_files"][v["input_index"]]["file_name"])
                )
                if not os.path.exists(input_file):
                    raise RuntimeError(
                        f"Bad flow, file from task_id=`{v['task_id']}`, index=`{v['input_index']}` not found."
                    )
                file_name = f"{task_id}_{param_name}" + Path(input_file).suffix
                result_path = os.path.join(options.INPUT_DIR, file_name)
                shutil.copy(input_file, result_path)
            elif "node_id" in v:
                input_file = ""
                result_prefix = f"{v['task_id']}_{v['node_id']}_"
                visionatrix_output_dir = os.path.join(options.OUTPUT_DIR, "visionatrix")
                for filename in os.listdir(visionatrix_output_dir):
                    if filename.startswith(result_prefix):
                        input_file = os.path.join(visionatrix_output_dir, filename)
                        break
                if not input_file or not os.path.exists(input_file):
                    raise RuntimeError(
                        f"Bad flow, file from task_id=`{v['task_id']}`, node_id={v['node_id']} not found."
                    )
                file_name = f"{task_id}_{param_name}" + Path(input_file).suffix
                result_path = os.path.join(options.INPUT_DIR, file_name)
                shutil.copy(input_file, result_path)
            elif "file_content" in v:
                file_name = f"{task_id}_{param_name}" + Path(v["remote_url"]).suffix
                result_path = os.path.join(options.INPUT_DIR, file_name)
                with builtins.open(result_path, mode="wb") as fp:
                    fp.write(v["file_content"])
            else:
                raise RuntimeError(
                    f"Bad flow, `input_index`, `node_id` or `file_content` "
                    f"should be present for '{param_name}' parameter."
                )
        else:
            file_name = f"{task_id}_{param_name}" + Path(v.filename).suffix
            result_path = os.path.join(options.INPUT_DIR, file_name)
            with builtins.open(result_path, mode="wb") as fp:
                v.file.seek(0)
                start_of_file = v.file.read(30)
                base64_index = start_of_file.find(b"base64,")
                if base64_index != -1:
                    v.file.seek(base64_index + len(b"base64,"))
                    fp.write(b64decode(v.file.read()))
                else:
                    v.file.seek(0)
                    shutil.copyfileobj(v.file, fp)
        for k, input_path in flow_input_file_params[param_name]["comfy_node_id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad workflow, node with id=`{k}` can not be found.")
            set_node_value(node, input_path, file_name)
        task_details["input_files"].append({"file_name": file_name, "file_size": os.path.getsize(result_path)})

    for node_to_disconnect in flow_input_file_params.values():
        if node_to_disconnect["name"] not in in_files_params:
            for node_id_to_disconnect in node_to_disconnect["comfy_node_id"]:
                disconnect_node_graph(node_id_to_disconnect, r)


def disconnect_node_graph(node_id: str, flow_comfy: dict[str, dict]) -> None:
    next_nodes_to_disconnect = []
    nodes_class_mappings = get_node_class_mappings()
    for next_node_id, next_node_details in flow_comfy.items():
        nodes_to_pop = []
        for input_id, input_details in next_node_details.get("inputs", {}).items():
            if isinstance(input_details, list) and input_details[0] == node_id:
                nodes_to_pop.append(input_id)
        for i in nodes_to_pop:
            class_type = next_node_details.get("class_type")
            if class_type is not None:
                node_class_mapping = nodes_class_mappings.get(class_type)
                if node_class_mapping is not None and hasattr(node_class_mapping, "INPUT_TYPES"):
                    next_node_input_types = node_class_mapping.INPUT_TYPES()
                    if "required" in next_node_input_types and i in next_node_input_types["required"]:
                        next_nodes_to_disconnect.append(next_node_id)
            next_node_details["inputs"].pop(i)
    flow_comfy.pop(node_id)
    for i in next_nodes_to_disconnect:
        disconnect_node_graph(i, flow_comfy)


def flow_prepare_output_params(
    outputs: list[str], task_id: int, task_details: dict, flow_comfy: dict[str, dict]
) -> None:
    for param in outputs:
        r_node = flow_comfy[param]
        if r_node["class_type"] in (
            "KSampler (Efficient)",
            "WD14Tagger|pysssss",
            "StringFunction|pysssss",
            "Evaluate Integers",
            "ShowText|pysssss",
            "MathExpression|pysssss",
            "PreviewImage",
            "Image Comparer (rgthree)",
        ):
            continue
        supported_outputs = SUPPORTED_OUTPUTS.keys()
        if r_node["class_type"] not in supported_outputs:
            raise RuntimeError(
                f"class_type={r_node['class_type']}: only {supported_outputs} nodes are supported currently as outputs"
            )
        if r_node["class_type"] == "SaveText|pysssss":
            r_node["inputs"]["file"] = f"visionatrix/{task_id}_{param}_.txt"
        else:
            r_node["inputs"]["filename_prefix"] = f"visionatrix/{task_id}_{param}"
        task_details["outputs"].append(
            {
                "comfy_node_id": int(param),
                "type": SUPPORTED_OUTPUTS[r_node["class_type"]],
                "file_size": -1,
                "batch_size": -1,
            }
        )


def process_seed_value(flow: Flow, in_texts_params: dict, flow_comfy: dict[str, dict]) -> None:
    if "seed" in [i["name"] for i in flow.input_params]:
        return  # skip automatic processing of "seed" if it was manually defined in "flow.json"
    random_seed = in_texts_params.get("seed", random.randint(1, 2147483647))
    for node_details in flow_comfy.values():
        if "inputs" in node_details:
            if "seed" in node_details["inputs"]:
                node_details["inputs"]["seed"] = random_seed
            elif (
                node_details["class_type"] in ("SamplerCustom", "RandomNoise", "KSamplerAdvanced")
                and "noise_seed" in node_details["inputs"]
            ):
                node_details["inputs"]["noise_seed"] = random_seed
    in_texts_params["seed"] = random_seed


def get_vix_flow(flow_comfy: dict[str, dict]) -> Flow:
    vix_flow = get_flow_metadata(flow_comfy)
    vix_flow["lora_connect_points"] = get_flow_lora_connect_points(flow_comfy)
    vix_flow["sub_flows"] = get_flow_subflows(flow_comfy)
    vix_flow["input_params"] = get_flow_inputs(flow_comfy, vix_flow["lora_connect_points"])
    vix_flow["models"] = process_flow_models(flow_comfy, {})
    return Flow.model_validate(vix_flow)


def get_flow_metadata(flow_comfy: dict[str, dict]) -> dict[str, str | list | dict]:
    for node_details in flow_comfy.values():
        if node_details["class_type"] == "VixUiWorkflowMetadata":
            r = node_details["inputs"].copy()
            for i in ("tags", "requires"):
                if value := node_details["inputs"].get(i):
                    r[i] = json.loads(value)
            return r
        if node_details.get("_meta", {}).get("title", "") == "WF_META":  # Text Multiline (Code Compatible)
            return json.loads(node_details["inputs"]["text"])
    raise ValueError("ComfyUI flow should contain Workflow metadata")


def get_flow_subflows(flow_comfy: dict[str, dict]) -> list[dict[str, str | list | dict]]:
    for node_details in flow_comfy.values():
        if node_details.get("_meta", {}).get("title", "") == "WF_SUBFLOWS":
            return json.loads(node_details["inputs"]["text"])
    return []


def get_flow_inputs(
    flow_comfy: dict[str, dict], loras_connection_points: dict[str, LoraConnectionPoint]
) -> list[dict[str, str | list | dict]]:
    input_params = []
    for node_id, node_details in flow_comfy.items():
        if not is_node_ui_input(node_details):
            continue
        class_type = str(node_details["class_type"])
        if node_details["class_type"] == "VixUiWorkflowMetadata":
            continue

        input_param_data = {
            "name": get_node_ui_name_id(node_id, node_details),
            "display_name": get_ui_input_attribute(node_details, "display_name"),
            "optional": get_ui_input_attribute(node_details, "optional"),
            "advanced": get_ui_input_attribute(node_details, "advanced"),
            "order": get_ui_input_attribute(node_details, "order"),
            "hidden": get_ui_input_attribute(node_details, "hidden"),
            "translatable": get_ui_input_attribute(node_details, "translatable"),
        }
        image_mask = bool(get_ui_input_attribute(node_details, "mask"))

        try:
            input_type, input_path = comfyui_class_info.CLASS_INFO[node_details["class_type"]]
            if image_mask is True and input_type == "image":
                input_type = "image-mask"
                source_input_name = get_ui_input_attribute(node_details, "source_input_name")
                if source_input_name:
                    input_param_data["source_input_name"] = source_input_name
                else:
                    raise ValueError("`source_input_name` required for mask parameter.")
        except KeyError as exc:
            raise ValueError(
                f"Node with class_type={node_details['class_type']} is not currently supported as input"
            ) from exc

        input_param_data.update(
            {
                "type": input_type,
                "default": get_node_value(node_details, input_path),
                "comfy_node_id": {node_id: input_path},
            }
        )
        if node_details["class_type"] in ("VixUiRangeFloat", "VixUiRangeScaleFloat", "VixUiRangeInt"):
            for ex_input in ("min", "max", "step"):
                input_param_data[ex_input] = node_details["inputs"][ex_input]
            if node_details["class_type"] == "VixUiRangeScaleFloat" and "source_input_name" in node_details["inputs"]:
                input_param_data["source_input_name"] = node_details["inputs"]["source_input_name"]
        elif node_details["class_type"] in ("VixUiList", "VixUiListLogic"):
            r = json.loads(node_details["inputs"]["possible_values"])
            if isinstance(r, list):
                input_param_data["options"] = {i: i for i in r}
            else:
                input_param_data["options"] = r
        elif class_type == "SDXLAspectRatioSelector":  # TO-DO: remove after release
            correct_aspect_ratio_default_options(input_param_data)
        elif class_type == "VixUiAspectRatioSelector":
            input_param_data["default"] = node_details["inputs"]["aspect_ratio"]
            input_param_data["options"] = {
                "1:1 (1024x1024)": "1:1 (1024x1024)",
                "2:3 (832x1216)": "2:3 (832x1216)",
                "3:4 (896x1152)": "3:4 (896x1152)",
                "5:8 (768x1216)": "5:8 (768x1216)",
                "9:16 (768x1344)": "9:16 (768x1344)",
                "9:19 (704x1472)": "9:19 (704x1472)",
                "9:21 (640x1536)": "9:21 (640x1536)",
                "3:2 (1216x832)": "3:2 (1216x832)",
                "4:3 (1152x896)": "4:3 (1152x896)",
                "8:5 (1216x768)": "8:5 (1216x768)",
                "16:9 (1344x768)": "16:9 (1344x768)",
                "19:9 (1472x704)": "19:9 (1472x704)",
                "21:9 (1536x640)": "21:9 (1536x640)",
            }
        input_params.append(input_param_data)
    add_loras_inputs(input_params, loras_connection_points)
    return sorted(input_params, key=lambda x: x["order"])


def correct_aspect_ratio_default_options(input_param_data: dict) -> None:
    _options = {
        "1:1 (1024x1024)": "1:1",
        "2:3 (832x1216)": "2:3",
        "3:4 (896x1152)": "3:4",
        "5:8 (768x1216)": "5:8",
        "9:16 (768x1344)": "9:16",
        "9:19 (704x1472)": "9:19",
        "9:21 (640x1536)": "9:21",
        "3:2 (1216x832)": "3:2",
        "4:3 (1152x896)": "4:3",
        "8:5 (1216x768)": "8:5",
        "16:9 (1344x768)": "16:9",
        "19:9 (1472x704)": "19:9",
        "21:9 (1536x640)": "21:9",
    }
    input_param_data["options"] = _options
    input_param_data["default"] = [i for i in _options if i.find(input_param_data["default"]) != -1][0]  # noqa


def is_node_ui_input(node_details: dict) -> bool:
    if str(node_details["class_type"]).startswith("VixUi"):
        return True
    return str(node_details["_meta"]["title"]).startswith("input;")


def get_node_ui_name_id(node_id: str, node_details: dict) -> str:
    custom_id = get_ui_input_attribute(node_details, "custom_id")
    return custom_id if custom_id else f"in_param_{node_id}"


def get_ollama_nodes(flow_comfy: dict[str, dict]) -> list[str]:
    r = []
    for node_id, node_details in flow_comfy.items():
        if str(node_details["class_type"]) in (
            "OllamaVision",
            "OllamaGenerate",
            "OllamaGenerateAdvance",
            "OllamaConnectivityV2",
        ):
            r.append(node_id)
    return r


def get_google_nodes(flow_comfy: dict[str, dict]) -> list[str]:
    r = []
    for node_id, node_details in flow_comfy.items():
        if str(node_details["class_type"]) == "Ask_Gemini":
            r.append(node_id)
    return r


def get_nodes_for_translate(
    input_params: dict[str, typing.Any], flow_comfy: dict[str, dict]
) -> list[dict[str, typing.Any]]:
    r = []
    for input_param, input_param_value in input_params.items():
        if input_param.startswith("in_param_"):
            node_info = flow_comfy[input_param[len("in_param_") :]]
        else:
            node_info = None
            for node_id, node_details in flow_comfy.items():
                if not is_node_ui_input(node_details):
                    continue
                if get_node_ui_name_id(node_id, node_details) == input_param:
                    node_info = node_details
                    break
            if not node_info:
                if input_param != "seed":
                    LOGGER.warning("Can not find node for `%s` input param.", input_param)
                continue
        if node_info.get("inputs", {}).get("translatable", False) and not is_english(input_param_value):
            r.append(
                {
                    "input_param_id": input_param,
                    "input_param_value": input_param_value,
                    "llm_prompt": "",
                }
            )
    return r


def get_remote_vae_switches(flow_comfy: dict[str, dict]) -> list[str]:
    r = []
    for node_id, node_details in flow_comfy.items():
        if str(node_details["_meta"]["title"]) == "remote_vae":
            r.append(node_id)
    return r


def get_insightface_nodes(flow_comfy: dict[str, dict]) -> list[str]:
    r = []
    for node_id, node_details in flow_comfy.items():
        if str(node_details["class_type"]) in (
            "InstantIDFaceAnalysis",
            "PulidInsightFaceLoader",
            "PhotoMakerInsightFaceLoader",
            "PulidFluxInsightFaceLoader",
            "InfiniteYouApply",
        ):
            r.append(node_id)
    return r


def is_flow_supported(flow: Flow, available_workers: list[WorkerDetails]) -> bool:
    if flow.is_macos_supported is False and not any(worker.device_type != "mps" for worker in available_workers):
        return False
    if flow.required_memory_gb:
        required_memory_bytes = flow.required_memory_gb * 1024 * 1024 * 1000  # GPU sometimes have less mem
        return any(worker.vram_total >= required_memory_bytes for worker in available_workers)
    return True


def fill_flows_supported_field(flows: dict[str, Flow], available_workers: list[WorkerDetails]) -> dict[str, Flow]:
    for flow in flows.values():
        flow.is_seed_supported = is_flow_supported(flow, available_workers)
    return flows


async def calculate_dynamic_fields_for_flows(flows: dict[str, Flow]) -> dict[str, Flow]:
    flows_with_filled_fields = await fill_flows_model_installed_field(flows)
    available_workers = await db_queries.get_workers_details(None, 3 * 60, "", include_federated=True)
    return fill_flows_supported_field(flows_with_filled_fields, available_workers)


async def create_new_flow(flow: Flow, flow_comfy: dict[str, dict], data: FlowCloneRequest) -> dict[str, dict]:
    """
    Creates a new ComfyUI workflow JSON (`flow_comfy`) from an existing flow by:
      1) Updating the metadata node (new name, display_name, etc.).
      2) Removing old dynamic LoRA from the original flow.
      3) Adding new dynamic LoRAs from `data.lora_connection_points` (each requiring a model URL).

    Returns the updated ComfyUI dict that can then be saved or validated as a new flow.
    """

    flow_comfy_new = deepcopy(flow_comfy)

    meta_node_id = None
    for node_id, node_details in flow_comfy_new.items():
        if node_details.get("class_type") == "VixUiWorkflowMetadata":
            meta_node_id = node_id
            break
        if node_details.get("_meta", {}).get("title", "") == "WF_META":
            meta_node_id = node_id
            break

    metadata_dict, mode = extract_metadata_dict(flow_comfy_new[meta_node_id])
    metadata_dict["name"] = data.new_name
    metadata_dict["display_name"] = data.metadata.display_name
    if data.metadata.description is not None:
        metadata_dict["description"] = data.metadata.description
    if data.metadata.license is not None:
        metadata_dict["license"] = data.metadata.license
    if data.metadata.required_memory_gb is not None:
        metadata_dict["required_memory_gb"] = data.metadata.required_memory_gb
    if data.metadata.version is not None:
        metadata_dict["version"] = data.metadata.version
    store_metadata_dict(flow_comfy_new[meta_node_id], metadata_dict, mode)

    for root_node_id, old_cp in flow.lora_connect_points.items():
        for old_lora_def in old_cp.connected_loras:
            flow_remove_model(flow_comfy_new, old_lora_def.name)
        remove_all_consecutive_loras_for_node(root_node_id, flow_comfy_new)

    if data.lora_connection_points:
        lora_connection_keys = list(flow.lora_connect_points.keys())
        for node_id in data.lora_connection_points:
            if node_id not in lora_connection_keys:
                raise ValueError(f"No such '{node_id}' LoRA connection point defined in flow: {lora_connection_keys}")

        for node_id, lora_details_list in data.lora_connection_points.items():
            for lora_details in reversed(lora_details_list):
                model_filename, trigger_words = await flow_add_model(
                    flow_comfy_new, lora_details.model_url, types=["loras"]
                )
                insert_lora_in_comfy_flow(
                    node_id,
                    lora_details.display_name,
                    lora_details.strength_model,
                    model_filename,
                    trigger_words,
                    flow_comfy_new,
                )

    return flow_comfy_new


def extract_metadata_dict(meta_node: dict) -> tuple[dict, str]:
    """
    Extracts metadata as a Python dictionary from either:
    1) `VixUiWorkflowMetadata` node (directly from `meta_node["inputs"]`) or
    2) `WF_META` node (JSON stored in `meta_node["inputs"]["text"]`).

    Returns: (metadata_dict, mode)
      - metadata_dict: the extracted dictionary of metadata
      - mode: either "direct" or "json" indicating which format is used
    """
    if meta_node.get("class_type") == "VixUiWorkflowMetadata":
        return dict(meta_node["inputs"]), "direct"
    if meta_node.get("_meta", {}).get("title", "") == "WF_META":
        return json.loads(meta_node["inputs"]["text"]), "json"
    return {}, "none"


def store_metadata_dict(meta_node: dict, metadata_dict: dict, mode: str) -> None:
    """Stores the updated metadata dictionary back into the node, depending on the `mode` ("direct" vs. "json")."""
    if mode == "direct":
        meta_node["inputs"] = metadata_dict
    elif mode == "json":
        meta_node["inputs"]["text"] = json.dumps(metadata_dict, indent=2)
