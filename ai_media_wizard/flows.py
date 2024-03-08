import builtins
import json
import logging
import os
import re
import time
from pathlib import Path
from shutil import rmtree
from typing import Any

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


def get_available_flows() -> [list[dict[str, Any]], list[dict[str, Any]]]:
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


def get_not_installed_flows(flows_dir: str, flows_comfy: list | None = None) -> list[dict[str, Any]]:
    installed_flows_ids = [i["name"] for i in get_installed_flows(flows_dir)]
    avail_flows, avail_flows_comfy = get_available_flows()
    r = []
    for i, v in enumerate(avail_flows):
        if v["name"] not in installed_flows_ids:
            r.append(v)
            if flows_comfy is not None:
                flows_comfy.append(avail_flows_comfy[i])
    return r


def get_installed_flows(flows_dir: str, flows_comfy: list | None = None) -> list[dict[str, Any]]:
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


def get_installed_flow(flows_dir: str, flow_name: str, flow_comfy: dict) -> dict[str, Any]:
    flows_comfy = []
    for i, flow in enumerate(get_installed_flows(flows_dir, flows_comfy)):
        if flow["name"] == flow_name:
            flow_comfy.clear()
            flow_comfy.update(flows_comfy[i])
            return flow
    return {}


def install_flow(flows_dir: str, flow_name: str, models_dir: str) -> str:
    flows, flows_comfy = get_available_flows()
    for i, flow in enumerate(flows):
        if flow["name"] == flow_name:
            install_custom_flow(flows_dir, flow, flows_comfy[i], models_dir)
    return f"Can't find `{flow_name}` flow in repository."


def install_custom_flow(flows_dir: str, flow: dir, flow_comfy: dir, models_dir: str) -> str:
    uninstall_flow(flows_dir, flow["name"])
    for model in flow["models"]:
        install_model(model, models_dir)
    local_flow_dir = os.path.join(flows_dir, flow["name"])
    os.mkdir(local_flow_dir)
    with builtins.open(os.path.join(local_flow_dir, "flow.json"), mode="w", encoding="utf-8") as fp:
        json.dump(flow, fp)
    with builtins.open(os.path.join(local_flow_dir, "flow_comfy.json"), mode="w", encoding="utf-8") as fp:
        json.dump(flow_comfy, fp)
    return ""


def uninstall_flow(flows_dir: str, flow_name: str) -> None:
    rmtree(os.path.join(flows_dir, flow_name), ignore_errors=True)


def prepare_flow_comfy(
    flow: dict, flow_comfy: dict, in_texts_params: dict, in_files_params: list, request_id: str, backend_dir: str
) -> dict:
    flow_params = flow["input_params"]
    text_params = [i for i in flow_params if i["type"] == "text"]
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
            node["inputs"][k_v["dest_field_name"]] = v
    min_required_files_count = len([i for i in files_params if not i.get("optional", False)])
    if len(in_files_params) < min_required_files_count:
        raise RuntimeError(f"{len(in_files_params)} files given, but {min_required_files_count} at least required.")
    for i, v in enumerate(in_files_params):
        file_name = os.path.join(backend_dir, "input", f"{request_id}_{i}")
        with builtins.open(file_name, mode="wb") as fp:
            if hasattr(v, "read"):
                fp.write(v.read())
            else:
                fp.write(bytes(v))
        for k, k_v in files_params[i]["comfy_node_id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad comfy flow or wizard flow, node with id=`{k}` can not be found.")
            node["inputs"][k_v["dest_field_name"]] = f"{request_id}_{i}"
    return r


def execute_flow_comfy(flow_comfy: dict, client_id: str) -> dict:
    r = httpx.post(f"http://127.0.0.1:{options.COMFY_PORT}/prompt", json={"prompt": flow_comfy, "client_id": client_id})
    if r.status_code != 200:
        raise RuntimeError(f"ComfyUI returned status: {r.status_code}")
    return json.loads(r.text)


def open_comfy_websocket(request_id: str):
    return connect(f"ws://127.0.0.1:{options.COMFY_PORT}/ws?clientId={request_id}")
