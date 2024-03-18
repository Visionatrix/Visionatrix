import builtins
import io
import json
import logging
import os
import re
import time
import typing
import zipfile
from pathlib import Path
from shutil import rmtree

import httpx

from . import options
from .models import install_model

LOGGER = logging.getLogger("visionatrix")
CACHE_AVAILABLE_FLOWS = {
    "update_time": time.time() - 11,
    "etag": "",
    "flows": [],
    "flows_comfy": [],
}


def get_available_flows() -> [list[dict[str, typing.Any]], list[dict[str, typing.Any]]]:
    if time.time() < CACHE_AVAILABLE_FLOWS["update_time"] + 10:
        return CACHE_AVAILABLE_FLOWS["flows"], CACHE_AVAILABLE_FLOWS["flows_comfy"]

    CACHE_AVAILABLE_FLOWS["update_time"] = time.time()
    r = httpx.get(options.FLOWS_URL, headers={"If-None-Match": CACHE_AVAILABLE_FLOWS["etag"]})
    if r.status_code == 304:
        return CACHE_AVAILABLE_FLOWS["flows"], CACHE_AVAILABLE_FLOWS["flows_comfy"]
    if r.status_code != 200:
        LOGGER.error("Request to get flows returned: %s", r.status_code)
        return CACHE_AVAILABLE_FLOWS["flows"], CACHE_AVAILABLE_FLOWS["flows_comfy"]
    r_flows = []
    r_flows_comfy = []
    with zipfile.ZipFile(io.BytesIO(r.content)) as zip_file:
        files_list = zip_file.namelist()
        directories = {name for name in zip_file.namelist() if name.endswith("/")}
        for directory in directories:
            flow_path = f"{directory}flow.json"
            flow_comfy_path = f"{directory}flow_comfy.json"
            if flow_path in files_list and flow_comfy_path in files_list:
                with zip_file.open(flow_path) as flow_file, zip_file.open(flow_comfy_path) as flow_comfy_file:
                    r_flows.append(json.loads(flow_file.read()))
                    r_flows_comfy.append(json.loads(flow_comfy_file.read()))
    CACHE_AVAILABLE_FLOWS.update({"flows": r_flows, "flows_comfy": r_flows_comfy, "etag": r.headers.get("etag", "")})
    return r_flows, r_flows_comfy


def get_not_installed_flows(flows_dir: str, flows_comfy: list | None = None) -> list[dict[str, typing.Any]]:
    installed_flows_ids = [i["name"] for i in get_installed_flows(flows_dir)]
    avail_flows, avail_flows_comfy = get_available_flows()
    r = []
    for i, v in enumerate(avail_flows):
        if v["name"] not in installed_flows_ids:
            r.append(v)
            if flows_comfy is not None:
                flows_comfy.append(avail_flows_comfy[i])
    return r


def get_installed_flows(flows_dir: str, flows_comfy: list | None = None) -> list[dict[str, typing.Any]]:
    flows = [entry for entry in Path(flows_dir).iterdir() if entry.is_dir()]
    r = []
    for flow in flows:
        flow_fp = flow.joinpath("flow.json")
        flow_comfy_fp = flow.joinpath("flow_comfy.json")
        if flow_fp.exists() is True and flow_comfy_fp.exists() is True:
            r.append(json.loads(flow_fp.read_bytes()))
            if flows_comfy is not None:
                flows_comfy.append(json.loads(flow_comfy_fp.read_bytes()))
    return r


def get_installed_flow(flows_dir: str, flow_name: str, flow_comfy: dict) -> dict[str, typing.Any]:
    flows_comfy = []
    for i, flow in enumerate(get_installed_flows(flows_dir, flows_comfy)):
        if flow["name"] == flow_name:
            flow_comfy.clear()
            flow_comfy.update(flows_comfy[i])
            return flow
    return {}


def install_custom_flow(
    flows_dir: str,
    flow: dir,
    flow_comfy: dir,
    models_dir: str,
    progress_callback: typing.Callable[[str, float, str], None] | None = None,
) -> None:
    uninstall_flow(flows_dir, flow["name"])
    progress_info = {
        "name": flow["name"],
        "current": 1.0,
        "progress_for_model": 97 / len(flow["models"]),
    }
    if progress_callback is not None:
        progress_callback(flow["name"], progress_info["current"], "")
    for model in flow["models"]:
        if not install_model(model, models_dir, progress_info, progress_callback):
            return
    local_flow_dir = os.path.join(flows_dir, flow["name"])
    os.mkdir(local_flow_dir)
    progress_info["current"] = 99.0
    if progress_callback is not None:
        progress_callback(flow["name"], progress_info["current"], "")
    with builtins.open(os.path.join(local_flow_dir, "flow.json"), mode="w", encoding="utf-8") as fp:
        json.dump(flow, fp)
    with builtins.open(os.path.join(local_flow_dir, "flow_comfy.json"), mode="w", encoding="utf-8") as fp:
        json.dump(flow_comfy, fp)
    progress_info["current"] = 100.0
    if progress_callback is not None:
        progress_callback(flow["name"], progress_info["current"], "")


def uninstall_flow(flows_dir: str, flow_name: str) -> None:
    rmtree(os.path.join(flows_dir, flow_name), ignore_errors=True)


def prepare_flow_comfy(
    flow: dict,
    flow_comfy: dict,
    in_texts_params: dict,
    in_files_params: list,
    task_id: int,
    task_details: dict,
    tasks_files_dir: str,
) -> dict:
    r = flow_comfy.copy()
    for i in [i for i in flow["input_params"] if i["type"] in ("text", "number", "list", "bool", "range")]:
        v = prepare_flow_comfy_get_input_value(in_texts_params, i)
        if v is None:
            continue
        for k, k_v in i["comfy_node_id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad comfy or visionatrix flow, node with id=`{k}` can not be found.")
            if i["type"] == "bool":
                v_copy = k_v["value"]
            elif "src_field_name" in k_v:
                v_copy = get_node_value(node, k_v["src_field_name"])
            else:
                v_copy = v
            for mod_operations in k_v.get("modify_param", []):
                for mod_operation, mod_params in mod_operations.items():
                    if mod_operation == "sub":
                        v_copy = re.sub(mod_params[0], mod_params[1], v_copy)
                    elif mod_operation == "sub-options":
                        for z in v:
                            if re.search(mod_params[0], z) is not None:
                                v_copy = re.sub(mod_params[0], v_copy, z)
                    else:
                        LOGGER.warning("Unknown modify param operation: %s", mod_operation)
            if convert_type := k_v.get("internal_type", ""):
                if convert_type == "int":
                    v_copy = int(v_copy)
                elif convert_type == "float":
                    v_copy = float(v_copy)
                else:
                    raise RuntimeError(f"Bad flow, unknown `internal_type` value: {convert_type}")
            set_node_value(node, k_v["dest_field_name"], v_copy)
    prepare_flow_comfy_files_params(flow, in_files_params, task_id, task_details, tasks_files_dir, r)
    prepare_output_params(flow, task_id, task_details, r)
    LOGGER.debug("Prepared flow data: %s", r)
    return r


def get_node_value(node: dict, path: list[str]) -> str | int | float:
    for key in path:
        node = node[key]
    return node


def set_node_value(node: dict, path: list[str], value: str | int | float) -> None:
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value


def prepare_flow_comfy_get_input_value(in_texts_params: dict, i: dict):
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
    flow: dict, in_files_params: list, task_id: int, task_details: dict, tasks_files_dir: str, r: dict
) -> None:
    files_params = [i for i in flow["input_params"] if i["type"] in ("image", "video")]
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
        with builtins.open(os.path.join(tasks_files_dir, "input", file_name), mode="wb") as fp:
            if hasattr(v, "read"):
                fp.write(v.read())
            else:
                fp.write(bytes(v))
            task_details["input_files"].append(file_name)


def prepare_output_params(flow: dict, task_id: int, task_details: dict, r: dict) -> None:
    for param in flow["output_params"]:
        node_id = param["comfy_node_id"]
        r_node = r[str(node_id)]
        if r_node["class_type"] != "SaveImage":
            raise RuntimeError(f"node={node_id}: only `SaveImage` nodes are supported currently as output nodes")
        r_node["inputs"]["filename_prefix"] = f"{task_id}_{node_id}"
        task_details["outputs"].append(node_id)
