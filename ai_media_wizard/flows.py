import builtins
import json
import logging
import os
import re
import time
import typing
from pathlib import Path
from shutil import rmtree

import httpx
from github import Github, GithubException
from websockets.sync.client import connect

from . import options
from .models import install_model

LOGGER = logging.getLogger("ai_media_wizard")
GH_CACHE_FLOWS = {}

CACHE_AVAILABLE_FLOWS = {
    "update_time": time.time() - 11,
    "flows": [],
    "flows_comfy": [],
}


def get_available_flows() -> [list[dict[str, typing.Any]], list[dict[str, typing.Any]]]:
    if time.time() < CACHE_AVAILABLE_FLOWS["update_time"] + 10:
        return CACHE_AVAILABLE_FLOWS["flows"], CACHE_AVAILABLE_FLOWS["flows_comfy"]

    CACHE_AVAILABLE_FLOWS["update_time"] = time.time()
    repo = Github().get_repo("cloud-media-flows/AI_Media_Wizard")
    r_flows = []
    r_flows_comfy = []
    for flow in repo.get_contents("flows"):
        if flow.type != "dir":
            continue
        if flow.name in GH_CACHE_FLOWS and flow.etag == GH_CACHE_FLOWS[flow.name]["etag"]:
            flow_data = GH_CACHE_FLOWS[flow.name]["flow_data"]
            flow_comfy_data = GH_CACHE_FLOWS[flow.name]["flow_comfy_data"]
        else:
            flow_dir = f"flows/{flow.name}"
            try:
                flow_data = json.loads(repo.get_contents(f"{flow_dir}/flow.json").decoded_content)
            except GithubException:
                LOGGER.warning("Can't load `flow.json` for %s, skipping.", flow.name)
                continue
            try:
                flow_comfy_data = json.loads(repo.get_contents(f"{flow_dir}/flow_comfy.json").decoded_content)
            except GithubException:
                LOGGER.warning("Can't load `flow_comfy.json` for %s, skipping.", flow.name)
                continue
            GH_CACHE_FLOWS.update({
                flow.name: {
                    "etag": flow.etag,
                    "flow_data": flow_data,
                    "flow_comfy_data": flow_comfy_data,
                }
            })
        r_flows.append(flow_data)
        r_flows_comfy.append(flow_comfy_data)
    CACHE_AVAILABLE_FLOWS.update({"flows": r_flows, "flows_comfy": r_flows_comfy})
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
    flow: dict, flow_comfy: dict, in_texts_params: dict, in_files_params: list, request_id: str, backend_dir: str
) -> dict:
    flow_params = flow["input_params"]
    text_params = [i for i in flow_params if i["type"] in ("text", "number")]
    files_params = [i for i in flow_params if i["type"] in ("image", "video")]
    r = flow_comfy.copy()
    for i in text_params:
        v = in_texts_params.get(i["name"], None)
        if v is None:
            if not i.get("optional", False):
                raise RuntimeError(f"Missing `{i['name']}` parameter.")
            continue
        for k, k_v in i["comfy_node_id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad comfy flow or wizard flow, node with id=`{k}` can not be found.")
            for mod_operation, mod_params in (k_v.get("modify_param", {})).items():
                if mod_operation == "sub":
                    v = re.sub(mod_params[0], mod_params[1], v)
                else:
                    LOGGER.warning("Unknown modify param operation: %s", mod_operation)
            if convert_type := k_v.get("internal_type", ""):
                if convert_type == "int":
                    v = int(v)
                elif convert_type == "float":
                    v = float(v)
                else:
                    raise RuntimeError(f"Bad flow, unknown `internal_type` value: {convert_type}")
            set_node_value(node, k_v["dest_field_name"], v)
    min_required_files_count = len([i for i in files_params if not i.get("optional", False)])
    if len(in_files_params) < min_required_files_count:
        raise RuntimeError(f"{len(in_files_params)} files given, but {min_required_files_count} at least required.")
    for i, v in enumerate(in_files_params):
        file_name = f"{request_id}_{i}"
        with builtins.open(os.path.join(backend_dir, "input", file_name), mode="wb") as fp:
            if hasattr(v, "read"):
                fp.write(v.read())
            else:
                fp.write(bytes(v))
        for k, k_v in files_params[i]["comfy_node_id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad comfy flow or wizard flow, node with id=`{k}` can not be found.")
            set_node_value(node, k_v["dest_field_name"], file_name)
    return r


def execute_flow_comfy(flow_comfy: dict, client_id: str) -> dict:
    r = httpx.post(f"http://{options.get_comfy_address()}/prompt", json={"prompt": flow_comfy, "client_id": client_id})
    if r.status_code != 200:
        LOGGER.error("ComfyUI rejected flow: %s", flow_comfy)
        raise RuntimeError(f"ComfyUI returned status: {r.status_code}")
    return json.loads(r.text)


def open_comfy_websocket(request_id: str):
    return connect(f"ws://{options.get_comfy_address()}/ws?clientId={request_id}")


def set_node_value(node: dict, path: list[str], value: str | int | float):
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
