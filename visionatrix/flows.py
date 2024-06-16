import builtins
import io
import json
import logging
import os
import random
import re
import shutil
import time
import typing
import zipfile
from pathlib import Path
from shutil import rmtree
from urllib.parse import urlparse

import httpx
from fastapi import UploadFile
from packaging.version import Version

from . import _version, database, options
from .models import install_model
from .models_map import fill_flow_models_from_comfy_flow
from .nodes_helpers import get_node_value, set_node_value
from .pydantic_models import Flow

LOGGER = logging.getLogger("visionatrix")
CACHE_AVAILABLE_FLOWS = {
    "update_time": time.time() - 11,
    "etag": "",
    "flows": [],
    "flows_comfy": [],
}
CACHE_INSTALLED_FLOWS = {
    "update_time": time.time() - 11,
    "flows": [],
    "flows_comfy": [],
}


def get_available_flows(flows_comfy: list) -> list[Flow]:
    if time.time() < CACHE_AVAILABLE_FLOWS["update_time"] + 10:
        flows_comfy.extend(CACHE_AVAILABLE_FLOWS["flows_comfy"])
        return CACHE_AVAILABLE_FLOWS["flows"]

    CACHE_AVAILABLE_FLOWS["update_time"] = time.time()
    flows_storage_url = options.FLOWS_URL
    if flows_storage_url.endswith("/"):
        vix_version = Version(_version.__version__)
        if vix_version.is_devrelease:
            flows_storage_url += "flows.zip"
        else:
            flows_storage_url += f"flows-{vix_version.major}.{vix_version.minor}.zip"
    if urlparse(flows_storage_url).scheme in ("http", "https", "ftp", "ftps"):
        r = httpx.get(flows_storage_url, headers={"If-None-Match": CACHE_AVAILABLE_FLOWS["etag"]})
        if r.status_code == 304:
            flows_comfy.extend(CACHE_AVAILABLE_FLOWS["flows_comfy"])
            return CACHE_AVAILABLE_FLOWS["flows"]
        if r.status_code != 200:
            LOGGER.error("Request to get flows returned: %s", r.status_code)
            flows_comfy.extend(CACHE_AVAILABLE_FLOWS["flows_comfy"])
            return CACHE_AVAILABLE_FLOWS["flows"]
        flows_content = r.content
        flows_content_etag = r.headers.get("etag", "")
    else:
        with builtins.open(flows_storage_url, mode="rb") as flows_archive:
            flows_content = flows_archive.read()
        flows_content_etag = ""
    r_flows = []
    r_flows_comfy = []
    with zipfile.ZipFile(io.BytesIO(flows_content)) as zip_file:
        files_list = zip_file.namelist()
        directories = {name for name in zip_file.namelist() if name.endswith("/")}
        for directory in directories:
            flow_path = f"{directory}flow.json"
            flow_comfy_path = f"{directory}flow_comfy.json"
            if flow_path in files_list and flow_comfy_path in files_list:
                with zip_file.open(flow_path) as flow_file, zip_file.open(flow_comfy_path) as flow_comfy_file:
                    _flow = Flow.model_validate(json.loads(flow_file.read()))
                    _flow_comfy = json.loads(flow_comfy_file.read())
                    fill_flow_models_from_comfy_flow(_flow, _flow_comfy)
                    r_flows.append(_flow)
                    r_flows_comfy.append(_flow_comfy)
    CACHE_AVAILABLE_FLOWS.update({"flows": r_flows, "flows_comfy": r_flows_comfy, "etag": flows_content_etag})
    flows_comfy.extend(CACHE_AVAILABLE_FLOWS["flows_comfy"])
    return r_flows


def get_not_installed_flows(flows_comfy: list | None = None) -> list[Flow]:
    installed_flows_ids = [i.name for i in get_installed_flows()]
    avail_flows_comfy = []
    avail_flows = get_available_flows(avail_flows_comfy)
    r = []
    for i, v in enumerate(avail_flows):
        if v.name not in installed_flows_ids:
            r.append(v)
            if flows_comfy is not None:
                flows_comfy.append(avail_flows_comfy[i])
    return r


def get_installed_flows(flows_comfy: list | None = None) -> list[Flow]:
    if time.time() < CACHE_INSTALLED_FLOWS["update_time"] + 10:
        if flows_comfy is not None:
            flows_comfy.extend(CACHE_INSTALLED_FLOWS["flows_comfy"])
        return CACHE_INSTALLED_FLOWS["flows"]

    CACHE_INSTALLED_FLOWS["update_time"] = time.time()
    flows = [entry for entry in Path(options.FLOWS_DIR).iterdir() if entry.is_dir()]
    r = []
    r_comfy = []
    for flow in flows:
        flow_fp = flow.joinpath("flow.json")
        flow_comfy_fp = flow.joinpath("flow_comfy.json")
        if flow_fp.exists() is True and flow_comfy_fp.exists() is True:
            _flow = Flow.model_validate(json.loads(flow_fp.read_bytes()))
            _flow_comfy = json.loads(flow_comfy_fp.read_bytes())
            fill_flow_models_from_comfy_flow(_flow, _flow_comfy)
            r.append(_flow)
            r_comfy.append(_flow_comfy)
    CACHE_INSTALLED_FLOWS.update({"flows": r, "flows_comfy": r_comfy})
    if flows_comfy is not None:
        flows_comfy.extend(r_comfy)
    return r


def get_installed_flows_names() -> list[str]:
    return [i.name for i in get_installed_flows()]


def get_installed_flow(flow_name: str, flow_comfy: dict[str, dict]) -> Flow | None:
    flows_comfy = []
    for i, flow in enumerate(get_installed_flows(flows_comfy)):
        if flow.name == flow_name:
            flow_comfy.clear()
            flow_comfy.update(flows_comfy[i])
            return flow
    return None


def install_custom_flow(
    flow: Flow,
    flow_comfy: dict,
    progress_callback: typing.Callable[[str, float, str], None] | None = None,
) -> None:
    uninstall_flow(flow.name)
    fill_flow_models_from_comfy_flow(flow, flow_comfy)
    progress_info = {
        "name": flow.name,
        "current": 1.0,
        "progress_for_model": 97 / len(flow.models),
    }
    if progress_callback is not None:
        progress_callback(flow.name, progress_info["current"], "")
    hf_auth_token = ""
    gated_models = [i for i in flow.models if i.gated]
    if gated_models and options.VIX_MODE != "SERVER":
        if "HF_AUTH_TOKEN" in os.environ:
            hf_auth_token = os.environ["HF_AUTH_TOKEN"]
        elif options.VIX_MODE == "DEFAULT":
            hf_auth_token = database.get_global_setting("huggingface_auth_token", True)
        else:
            r = httpx.get(
                options.VIX_SERVER.rstrip("/") + "/setting",
                params={"key": "huggingface_auth_token"},
                auth=options.worker_auth(),
                timeout=float(options.WORKER_NET_TIMEOUT),
            )
            if not httpx.codes.is_error(r.status_code):
                hf_auth_token = r.text
        if not hf_auth_token:
            LOGGER.warning("Flow has gated model(s): %s; AccessToken was not found.", [i.name for i in gated_models])
    for model in flow.models:
        if not install_model(model, progress_info, progress_callback, hf_auth_token):
            return
    local_flow_dir = os.path.join(options.FLOWS_DIR, flow.name)
    os.mkdir(local_flow_dir)
    progress_info["current"] = 99.0
    if progress_callback is not None:
        progress_callback(flow.name, progress_info["current"], "")
    with builtins.open(os.path.join(str(local_flow_dir), "flow.json"), mode="w", encoding="utf-8") as fp:
        fp.write(flow.model_dump_json(indent=2))
    with builtins.open(os.path.join(str(local_flow_dir), "flow_comfy.json"), mode="w", encoding="utf-8") as fp:
        json.dump(flow_comfy, fp)
    progress_info["current"] = 100.0
    CACHE_INSTALLED_FLOWS["update_time"] = 0
    if progress_callback is not None:
        progress_callback(flow.name, progress_info["current"], "")


def uninstall_flow(flow_name: str) -> None:
    rmtree(os.path.join(options.FLOWS_DIR, flow_name), ignore_errors=True)
    CACHE_INSTALLED_FLOWS["update_time"] = 0


def prepare_flow_comfy(
    flow: Flow,
    flow_comfy: dict,
    in_texts_params: dict,
    in_files_params: list[UploadFile | dict],
    task_details: dict,
) -> dict:
    r = flow_comfy.copy()
    for i in [i for i in flow.input_params if i["type"] in ("text", "number", "list", "bool", "range", "range_scale")]:
        v = prepare_flow_comfy_get_input_value(in_texts_params, i)
        if v is None:
            continue
        for k, k_v in i["comfy_node_id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad comfy or visionatrix flow, node with id=`{k}` can not be found.")
            if "src_field_name" in k_v:
                v_copy = get_node_value(node, k_v["src_field_name"])
            elif i["type"] == "bool" and "value" in k_v:
                v_copy = k_v["value"]
            else:
                v_copy = v
            for mod_operations in k_v.get("modify_param", []):
                for mod_operation, mod_params in mod_operations.items():
                    if mod_operation == "sub":
                        if len(mod_params) == 1 and "src_field_name" in k_v:
                            v_copy = re.sub(mod_params[0], v, v_copy)
                        else:
                            v_copy = re.sub(mod_params[0], mod_params[1], v_copy)
                    elif mod_operation == "sub-options":
                        for z in v:
                            if re.search(mod_params[0], z) is not None:
                                v_copy = re.sub(mod_params[0], v_copy, z)
                    else:
                        LOGGER.warning("Unknown modify param operation: %s", mod_operation)
            perform_node_connections(r, k, k_v)
            if convert_type := k_v.get("internal_type", ""):
                if convert_type == "int":
                    v_copy = int(v_copy)
                elif convert_type == "float":
                    v_copy = float(v_copy)
                else:
                    raise RuntimeError(f"Bad flow, unknown `internal_type` value: {convert_type}")
            if "dest_field_name" in k_v:
                set_node_value(node, k_v["dest_field_name"], v_copy)
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
            v = int(v)
        v = bool(v)
        if not v:
            return None  # we perform action from "bool" only when condition is True, skip otherwise
    return v


def prepare_flow_comfy_files_params(
    flow: Flow, in_files_params: list[UploadFile | dict], task_id: int, task_details: dict, r: dict
) -> None:
    files_params = [i for i in flow.input_params if i["type"] in ("image", "video")]
    min_required_files_count = len([i for i in files_params if not i.get("optional", False)])
    if len(in_files_params) < min_required_files_count:
        raise RuntimeError(f"{len(in_files_params)} files given, but {min_required_files_count} at least required.")
    for i, v in enumerate(in_files_params):
        file_name = f"{task_id}_{i}"
        for k, k_v in files_params[i]["comfy_node_id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad comfy or visionatrix flow, node with id=`{k}` can not be found.")
            set_node_value(node, k_v["dest_field_name"], file_name)
            perform_node_connections(r, k, k_v)
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
                raise RuntimeError("Bad flow, `input_index` or `node_id` should be present.")
        else:
            with builtins.open(result_path, mode="wb") as fp:
                v.file.seek(0)
                shutil.copyfileobj(v.file, fp)
        task_details["input_files"].append({"file_name": file_name, "file_size": os.path.getsize(result_path)})


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
        ):
            continue
        if r_node["class_type"] != "SaveImage":
            raise RuntimeError(
                f"class_type={r_node['class_type']}: only `SaveImage` nodes are supported currently as output node"
            )
        r_node["inputs"]["filename_prefix"] = f"{task_id}_{param}"
        task_details["outputs"].append({"comfy_node_id": int(param), "type": "image", "file_size": -1})


def process_seed_value(flow: Flow, in_texts_params: dict, flow_comfy: dict[str, dict]) -> None:
    if "seed" in [i["name"] for i in flow.input_params]:
        return  # skip automatic processing of "seed" if it was manually defined in "flow.json"
    random_seed = in_texts_params.get("seed", random.randint(1, 3999999999))
    for node_details in flow_comfy.values():
        if "inputs" in node_details:
            if "seed" in node_details["inputs"]:
                node_details["inputs"]["seed"] = random_seed
            elif node_details["class_type"] == "SamplerCustom" and "noise_seed" in node_details["inputs"]:
                node_details["inputs"]["noise_seed"] = random_seed
    in_texts_params["seed"] = random_seed


def perform_node_connections(flow_comfy: dict[str, dict], node_id: str, node_details: dict) -> None:
    if "node_connect" not in node_details:
        return
    target_connect = node_details["node_connect"]
    set_node_value(flow_comfy[target_connect["node_id"]], target_connect["dest_field_name"], [node_id, 0])
