import builtins
import concurrent.futures
import contextlib
import io
import json
import logging
import math
import os
import random
import shutil
import threading
import time
import typing
import zipfile
from base64 import b64decode
from copy import deepcopy
from urllib.parse import urlparse

import httpx
from packaging.version import Version, parse
from starlette.datastructures import UploadFile as StarletteUploadFile

from . import _version, comfyui_class_info, db_queries, events, options
from .comfyui_wrapper import get_node_class_mappings
from .etc import is_english
from .models import fill_flows_model_installed_field, install_model
from .models_map import process_flow_models
from .nodes_helpers import get_node_value, set_node_value
from .pydantic_models import Flow

SECONDS_TO_CACHE_INSTALLED_FLOWS = 10
SECONDS_TO_CACHE_AVAILABLE_FLOWS = 3 * 60

LOGGER = logging.getLogger("visionatrix")
CACHE_AVAILABLE_FLOWS = {}
CACHE_INSTALLED_FLOWS = {
    "update_time": time.time() - (SECONDS_TO_CACHE_INSTALLED_FLOWS + 1),
    "flows": {},
    "flows_comfy": {},
}
CACHE_INSTALLED_FLOWS_LOCK = threading.Lock()
CACHE_INSTALLED_FLOWS_EVENT = threading.Condition(CACHE_INSTALLED_FLOWS_LOCK)

SUPPORTED_OUTPUTS = {
    "SaveImage": "image",
    "SaveAnimatedWEBP": "image-animated",
    "VHS_VideoCombine": "video",
}

SUPPORTED_TEXT_TYPES_INPUTS = ["text", "number", "list", "bool", "range", "range_scale"]
SUPPORTED_FILE_TYPES_INPUTS = ["image", "image-mask", "video"]


def get_available_flows(flows_comfy: dict[str, dict] | None = None) -> dict[str, Flow]:
    if flows_comfy is None:
        flows_comfy = {}
    else:
        flows_comfy.clear()

    flows_storage_urls = [url.strip() for url in options.FLOWS_URL.split(";") if url.strip()]
    if not flows_storage_urls:
        LOGGER.warning("'FLOWS_URL' is empty. Unable to get available flows.")
        return {}

    combined_flows = {}
    combined_flows_comfy = {}

    for flows_storage_url in flows_storage_urls:
        cache_entry = CACHE_AVAILABLE_FLOWS.get(flows_storage_url, {})
        current_time = time.time()
        cache_expired = current_time > cache_entry.get("update_time", 0) + SECONDS_TO_CACHE_AVAILABLE_FLOWS

        if cache_expired or not cache_entry:
            etag = cache_entry.get("etag", "")
            flows, flows_comfy_single, new_etag = fetch_flows_from_url_or_path(flows_storage_url, etag)
            if flows is not None:
                # Update cache_entry with new data
                cache_entry = {
                    "update_time": current_time,
                    "etag": new_etag,
                    "flows": flows,
                    "flows_comfy": flows_comfy_single,
                }
                CACHE_AVAILABLE_FLOWS[flows_storage_url] = cache_entry
            else:
                # Use existing cache_entry (even if expired)
                flows = cache_entry.get("flows", {})
                flows_comfy_single = cache_entry.get("flows_comfy", {})
        else:
            # Cache is valid, use cached data
            flows = cache_entry.get("flows", {})
            flows_comfy_single = cache_entry.get("flows_comfy", {})

        # Merge the flows into combined_flows
        for flow_name, flow_data in flows.items():
            if flow_name not in combined_flows:
                combined_flows[flow_name] = flow_data
                combined_flows_comfy[flow_name] = flows_comfy_single[flow_name]
            else:
                # Handle duplicate flow names, prefer the latest version
                existing_version = parse(combined_flows[flow_name].version)
                new_version = parse(flow_data.version)
                if new_version > existing_version:
                    combined_flows[flow_name] = flow_data
                    combined_flows_comfy[flow_name] = flows_comfy_single[flow_name]

    flows_comfy.update(combined_flows_comfy)
    return combined_flows


def fetch_flows_from_url_or_path(flows_storage_url: str, etag: str):
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
            r = httpx.get(flows_storage_url, headers={"If-None-Match": etag}, timeout=5.0)
        except httpx.TransportError as e:
            LOGGER.error("Request to get flows failed with: %s", str(e))
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
            LOGGER.error("Failed to read flows archive at %s: %s", flows_storage_url, str(e))
            return None, None, etag

    try:
        with zipfile.ZipFile(io.BytesIO(flows_content)) as zip_file:
            for flow_comfy_path in {name for name in zip_file.namelist() if name.endswith(".json")}:
                with zip_file.open(flow_comfy_path) as flow_comfy_file:
                    _flow_comfy = json.loads(flow_comfy_file.read())
                    _flow = get_vix_flow(_flow_comfy)
                    _flow_name = _flow.name.lower()
                    r_flows[_flow_name] = _flow
                    r_flows_comfy[_flow_name] = _flow_comfy
    except Exception as e:
        LOGGER.error("Failed to parse flows from %s: %s", flows_storage_url, str(e))
        return None, None, etag

    return r_flows, r_flows_comfy, flows_content_etag


def get_not_installed_flows(flows_comfy: dict[str, dict] | None = None) -> dict[str, Flow]:
    installed_flows_ids = list(get_installed_flows())
    avail_flows_comfy = {}
    avail_flows = get_available_flows(avail_flows_comfy)
    flows = {}
    for i, v in avail_flows.items():
        if i not in installed_flows_ids:
            flows[i] = v
            if flows_comfy is not None:
                flows_comfy[i] = avail_flows_comfy[i]
    return flows


def get_installed_flows(flows_comfy: dict[str, dict] | None = None) -> dict[str, Flow]:
    if flows_comfy is None:
        flows_comfy = {}
    else:
        flows_comfy.clear()
    current_time = time.time()

    # Acquire the lock
    with CACHE_INSTALLED_FLOWS_LOCK:
        # Check cache validity after acquiring lock
        cache_expiry_time = CACHE_INSTALLED_FLOWS["update_time"] + SECONDS_TO_CACHE_INSTALLED_FLOWS
        if current_time < cache_expiry_time:
            flows_comfy.update(CACHE_INSTALLED_FLOWS["flows_comfy"])
            return CACHE_INSTALLED_FLOWS["flows"]

        # If another thread is updating the cache, wait
        if CACHE_INSTALLED_FLOWS.get("updating", False):
            while CACHE_INSTALLED_FLOWS.get("updating", False):
                CACHE_INSTALLED_FLOWS_EVENT.wait()
            # Re-check cache validity after being notified
            cache_expiry_time = CACHE_INSTALLED_FLOWS["update_time"] + SECONDS_TO_CACHE_INSTALLED_FLOWS
            if current_time < cache_expiry_time:
                flows_comfy.update(CACHE_INSTALLED_FLOWS["flows_comfy"])
                return CACHE_INSTALLED_FLOWS["flows"]
        # Set the updating flag to indicate cache is being updated
        CACHE_INSTALLED_FLOWS["updating"] = True

    # Release the lock before performing long-running operations
    # Perform the operations without holding the lock
    updated_data = _update_installed_flows()

    # Acquire the lock again to update the cache
    with CACHE_INSTALLED_FLOWS_LOCK:
        # Update the cache with new data
        CACHE_INSTALLED_FLOWS.update(updated_data)
        CACHE_INSTALLED_FLOWS["update_time"] = time.time()
        CACHE_INSTALLED_FLOWS["updating"] = False  # Clear the updating flag
        # Notify all waiting threads that the cache has been updated
        CACHE_INSTALLED_FLOWS_EVENT.notify_all()

    # Update flows_comfy with the new cache data
    flows_comfy.update(CACHE_INSTALLED_FLOWS["flows_comfy"])
    return CACHE_INSTALLED_FLOWS["flows"]


def _update_installed_flows():
    available_flows = get_available_flows({})
    public_flows_names = list(available_flows)
    installed_flows = db_queries.get_installed_flows()
    r = {}
    r_comfy = {}
    for installed_flow in installed_flows:
        installed_flow.flow = get_vix_flow(installed_flow.flow_comfy)
        if installed_flow.name not in public_flows_names:
            installed_flow.flow.private = True
        _fresh_flow_info = available_flows.get(installed_flow.name)
        if _fresh_flow_info and parse(installed_flow.flow.version) < parse(_fresh_flow_info.version):
            installed_flow.flow.new_version_available = _fresh_flow_info.version
        r[installed_flow.name] = installed_flow.flow
        r_comfy[installed_flow.name] = installed_flow.flow_comfy
    return {"flows": r, "flows_comfy": r_comfy}


def get_installed_flow(flow_name: str, flow_comfy: dict[str, dict]) -> Flow | None:
    flows_comfy = {}
    flow = get_installed_flows(flows_comfy).get(flow_name)
    if flow:
        flow_comfy.clear()
        flow_comfy.update(flows_comfy[flow_name])
    return flow


def install_custom_flow(flow: Flow, flow_comfy: dict) -> bool:
    db_queries.delete_flow_progress_install(flow.name)
    db_queries.add_flow_progress_install(flow.name, flow_comfy)
    progress_for_model = 97 / max(len(flow.models), 1)
    if not __flow_install_callback(flow.name, 1.0, "", False):
        return False
    auth_tokens = {"huggingface_auth_token": "", "civitai_auth_token": ""}
    for token_env, token_key in [("HF_AUTH_TOKEN", "huggingface_auth_token"), ("CA_AUTH_TOKEN", "civitai_auth_token")]:
        if token_env in os.environ:
            auth_tokens[token_key] = os.environ[token_env]
        elif options.VIX_MODE == "WORKER" and options.VIX_SERVER:
            try:
                r = httpx.get(
                    options.VIX_SERVER.rstrip("/") + "/setting",
                    params={"key": token_key},
                    auth=options.worker_auth(),
                    timeout=float(options.WORKER_NET_TIMEOUT),
                )
                if not httpx.codes.is_error(r.status_code):
                    auth_tokens[token_key] = r.text.strip()
            except Exception as e:
                LOGGER.error("Error fetching `%s`: %s", token_key, str(e))
        else:
            auth_tokens[token_key] = db_queries.get_global_setting(token_key, True)

    try:
        install_models_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    install_model,
                    model,
                    flow.name,
                    progress_for_model,
                    __flow_install_callback,
                    (auth_tokens["huggingface_auth_token"], auth_tokens["civitai_auth_token"]),
                )
                for model in flow.models
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    install_models_result = future.result()
                    install_models_results.append(install_models_result)
                except Exception as e:
                    LOGGER.exception("Error during models installation: %s", e)
                    return False
    except KeyboardInterrupt:
        # this will only work for the "install-flow" command when run from terminal
        events.EXIT_EVENT.set()
        for future in futures:
            with contextlib.suppress(Exception):
                future.result()
        return False

    if not all(install_models_results):
        LOGGER.info("Installation of `%s` was unsuccessful", flow.name)
        return False

    if not __flow_install_callback(flow.name, 100.0, "", False):
        return False
    CACHE_INSTALLED_FLOWS["update_time"] = 0
    return True


def __flow_install_callback(name: str, progress: float, error: str, relative_progress: bool) -> bool:
    """Returns `True` if no errors occurred."""

    if error:
        LOGGER.error("`%s` installation failed: %s", name, error)
        db_queries.set_flow_progress_install_error(name, error)
        return False  # we return "False" because we are setting an error and "installation" should be stopped anyway
    if progress == 100.0:
        LOGGER.info("Installation of %s flow completed", name)
        return db_queries.update_flow_progress_install(name, progress, False)

    if events.EXIT_EVENT.is_set():
        db_queries.set_flow_progress_install_error(name, "Installation interrupted by user.")
        return False

    if LOGGER.getEffectiveLevel() <= logging.INFO:
        current_progress_info = db_queries.get_flow_progress_install(name)
        if not current_progress_info:
            LOGGER.warning("Can not get installation progress info for %s", name)
        else:
            LOGGER.info(
                "`%s` installation: %s", name, math.floor((current_progress_info.progress + progress) * 10) / 10
            )
    return db_queries.update_flow_progress_install(name, progress, relative_progress)


def uninstall_flow(flow_name: str) -> None:
    db_queries.delete_flow_progress_install(flow_name)
    CACHE_INSTALLED_FLOWS["update_time"] = 0


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
        file_name = f"{task_id}_{param_name}"
        for k, input_path in flow_input_file_params[param_name]["comfy_node_id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad workflow, node with id=`{k}` can not be found.")
            set_node_value(node, input_path, file_name)
        result_path = os.path.join(options.TASKS_FILES_DIR, "input", file_name)
        if isinstance(v, dict):
            if "input_index" in v:
                input_file = os.path.join(options.TASKS_FILES_DIR, "input", f"{v['task_id']}_{v['input_index']}")
                if not os.path.exists(input_file):
                    raise RuntimeError(
                        f"Bad flow, file from task_id=`{v['task_id']}`, index=`{v['input_index']}` not found."
                    )
                shutil.copy(input_file, result_path)
            elif "node_id" in v:
                input_file = ""
                result_prefix = f"{v['task_id']}_{v['node_id']}_"
                output_directory = os.path.join(options.TASKS_FILES_DIR, "output")
                for filename in os.listdir(output_directory):
                    if filename.startswith(result_prefix):
                        input_file = os.path.join(output_directory, filename)
                if not input_file or not os.path.exists(input_file):
                    raise RuntimeError(
                        f"Bad flow, file from task_id=`{v['task_id']}`, node_id={v['node_id']} not found."
                    )
                shutil.copy(input_file, result_path)
            else:
                raise RuntimeError(
                    f"Bad flow, `input_index` or `node_id` should be present for '{param_name}' parameter."
                )
        else:
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
        ):
            continue
        supported_outputs = SUPPORTED_OUTPUTS.keys()
        if r_node["class_type"] not in supported_outputs:
            raise RuntimeError(
                f"class_type={r_node['class_type']}: only {supported_outputs} nodes are supported currently as outputs"
            )
        r_node["inputs"]["filename_prefix"] = f"{task_id}_{param}"
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
    random_seed = in_texts_params.get("seed", random.randint(1, 3999999999))
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
    vix_flow["sub_flows"] = get_flow_subflows(flow_comfy)
    vix_flow["input_params"] = get_flow_inputs(flow_comfy)
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


def get_flow_inputs(flow_comfy: dict[str, dict]) -> list[dict[str, str | list | dict]]:
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
        elif class_type == "SDXLAspectRatioSelector":
            correct_aspect_ratio_default_options(input_param_data)
        input_params.append(input_param_data)
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


def get_ui_input_attribute(node_details: dict, attr_name: str) -> bool | str | int:
    attributes_defaults = {
        "optional": False,
        "advanced": False,
        "translatable": False,
        "hidden": False,
        "mask": False,
        "order": 99,
        "custom_id": "",
        "source_input_name": None,
    }

    if str(node_details["class_type"]).startswith("VixUi"):
        return node_details["inputs"].get(attr_name, attributes_defaults.get(attr_name))

    input_info = str(node_details["_meta"]["title"]).split(";")
    input_info = [i.strip() for i in input_info]

    if attr_name == "display_name":
        return input_info[1] if len(input_info) > 1 else ""

    other_attributes = [s.lower() for s in input_info[2:]]
    for attribute in other_attributes:
        if "=" in attribute:
            key, value = attribute.split("=", 1)
            if key == attr_name:
                return int(value) if attr_name == "order" else value
        elif attribute == attr_name:
            return True
    return attributes_defaults.get(attr_name)


def get_node_ui_name_id(node_id: str, node_details: dict) -> str:
    custom_id = get_ui_input_attribute(node_details, "custom_id")
    return custom_id if custom_id else f"in_param_{node_id}"


def get_ollama_nodes(flow_comfy: dict) -> list[str]:
    r = []
    for node_id, node_details in flow_comfy.items():
        if str(node_details["class_type"]) in ("OllamaVision", "OllamaGenerate", "OllamaGenerateAdvance"):
            r.append(node_id)
    return r


def get_google_nodes(flow_comfy: dict) -> list[str]:
    r = []
    for node_id, node_details in flow_comfy.items():
        if str(node_details["class_type"]) == "Ask_Gemini":
            r.append(node_id)
    return r


def get_nodes_for_translate(input_params: dict[str, typing.Any], flow_comfy: dict) -> list[dict[str, typing.Any]]:
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


async def fill_flows_supported_field(flows: dict[str, Flow]) -> dict[str, Flow]:
    available_workers = db_queries.get_workers_details(None, 5 * 60, "")
    for flow in flows.values():
        if flow.is_macos_supported is False:
            flow.is_supported_by_workers = any(worker.device_type != "mps" for worker in available_workers)
        if flow.is_supported_by_workers is False:
            continue  # Flow already marked as unsupported, skip additional checks
        if flow.required_memory_gb:
            required_memory_bytes = flow.required_memory_gb * 1024**3
            # Check if any worker has sufficient available memory
            flow.is_supported_by_workers = any(
                worker.vram_total >= required_memory_bytes for worker in available_workers
            )
    return flows


async def calculate_dynamic_fields_for_flows(flows: dict[str, Flow]) -> dict[str, Flow]:
    flows_with_filled_fields = await fill_flows_model_installed_field(flows)
    return await fill_flows_supported_field(flows_with_filled_fields)
