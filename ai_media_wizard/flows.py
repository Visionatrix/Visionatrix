import builtins
import json
import os
import re
from pathlib import Path
from shutil import rmtree
from typing import Any

import httpx
from github import Github, GithubException
from websockets.sync.client import connect

from . import options

GH_CACHE_FLOWS = {}


def get_available_flows(flows_dir: str, comfy_flows: list | None = None) -> list[dict[str, Any]]:
    repo = Github().get_repo("cloud-media-flows/AI_Media_Wizard")
    installed_flows_ids = [i["name"] for i in get_installed_flows(flows_dir)]
    possible_flows = []
    for flow in repo.get_contents("flows"):
        if flow.type != "dir":
            continue
        if flow.name in GH_CACHE_FLOWS and flow.etag == GH_CACHE_FLOWS[flow.name]["etag"]:
            flow_data = GH_CACHE_FLOWS[flow.name]["flow_data"]
            comfy_flow_data = GH_CACHE_FLOWS[flow.name]["comfy_flow_data"]
        else:
            flow_dir = f"flows/{flow.name}"
            try:
                flow_description = repo.get_contents(f"{flow_dir}/flow.json")
            except GithubException:
                print(f"Warning, can't find `flow.json` for {flow.name}, skipping.")
                continue
            flow_data = json.loads(flow_description.decoded_content)
            comfy_flow = flow_data.get("comfy_flow", "")
            if not comfy_flow:
                print(f"Warning, broken flow file: {flow_dir}/flow.json")
                continue
            try:
                comfy_flow_data = repo.get_contents(f"{flow_dir}/{comfy_flow}")
            except GithubException:
                print(f"Can't find `comfy flow` at ({flow_dir}/{comfy_flow}) for {flow.name}, skipping.")
                continue
            comfy_flow_data = json.loads(comfy_flow_data.decoded_content)
            GH_CACHE_FLOWS.update({
                flow.name: {
                    "etag": flow.etag,
                    "flow_data": flow_data,
                    "comfy_flow_data": comfy_flow_data,
                }
            })
        if flow_data["name"] not in installed_flows_ids:
            possible_flows.append(flow_data)
            if comfy_flows is not None:
                comfy_flows.append(comfy_flow_data)
    return possible_flows


def get_installed_flows(flows_dir: str, comfy_flows: list | None = None) -> list[dict[str, Any]]:
    flows = [entry for entry in Path(flows_dir).iterdir() if entry.is_dir()]
    r = []
    for flow in flows:
        if (flow_fp := flow.joinpath("flow.json")).exists() is True:
            flow_data = json.loads(flow_fp.read_bytes())
            if (comfy_flow_fp := flow.joinpath(flow_data["comfy_flow"])).exists() is True:
                r.append(flow_data)
                if comfy_flows is not None:
                    comfy_flows.append(json.loads(comfy_flow_fp.read_bytes()))
    return r


def get_installed_flow(flows_dir: str, flow_name: str, comfy_flow: dict) -> dict[str, Any]:
    comfy_flows = []
    for i, flow in enumerate(get_installed_flows(flows_dir, comfy_flows)):
        if flow["name"] == flow_name:
            comfy_flow.clear()
            comfy_flow.update(comfy_flows[i])
            return flow
    return {}


def install_flow(flows_dir: str, flow_name: str, models_dir: str) -> str:
    uninstall_flow(flows_dir, flow_name)
    comfy_flows_data = []
    for i, flow in enumerate(get_available_flows(flows_dir, comfy_flows_data)):
        if flow["name"] == flow_name:
            for model in flow["models"]:
                download_model(model, models_dir)
            local_flow_dir = os.path.join(flows_dir, flow_name)
            os.mkdir(local_flow_dir)
            with builtins.open(os.path.join(local_flow_dir, "flow.json"), mode="w", encoding="utf-8") as fp:
                json.dump(flow, fp)
            with builtins.open(os.path.join(local_flow_dir, flow["comfy_flow"]), mode="w", encoding="utf-8") as fp:
                json.dump(comfy_flows_data[i], fp)
            return ""
    return f"Can't find `{flow_name}` flow in repository."


def uninstall_flow(flows_dir: str, flow_name: str) -> None:
    rmtree(os.path.join(flows_dir, flow_name), ignore_errors=True)


def download_model(model: dict[str, str], models_dir: str) -> None:
    save_path = Path(models_dir).joinpath(model["save_path"])
    if save_path.exists():
        print(f"`{save_path}` already exists, skipping.")
        return
    with httpx.stream("GET", model["url"], follow_redirects=True) as response:
        if not response.is_success:
            raise RuntimeError(f"Downloading of '{model['url']}' returned {response.status_code} status.")
        os.makedirs(save_path.parent, exist_ok=True)
        try:
            with builtins.open(save_path, "wb") as file:
                for chunk in response.iter_bytes(5 * 1024 * 1024):
                    file.write(chunk)
        except Exception:  # noqa pylint: disable=broad-exception-caught
            rmtree(save_path.parent)
            raise RuntimeError(f"Error during downloading '{model['url']}'.") from None


def prepare_comfy_flow(
    flow: dict, comfy_flow: dict, in_texts_params: dict, in_files_params: list, request_id: str, backend_dir: str
) -> dict:
    flow_params = flow["input_params"]
    text_params = [i for i in flow_params if i["type"] == "text"]
    files_params = [i for i in flow_params if i["type"] in ("image", "video")]
    r = comfy_flow.copy()
    for i in text_params:
        v = in_texts_params.get(i["name"], None)
        if v is None:
            if not i.get("optional", False):
                raise RuntimeError(f"Missing `{i['name']}` parameter.")
            continue
        for k, k_v in i["id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad comfy flow or wizard flow, node with id=`{k}` can not be found.")
            for mod_operation, mod_params in (k_v.get("modify_param", {})).items():
                if mod_operation == "sub":
                    v = re.sub(mod_params[0], mod_params[1], v)
                else:
                    print(f"Warning! Unknown modify param operation: {mod_operation}")
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
        for k, k_v in files_params[i]["id"].items():
            node = r.get(k, {})
            if not node:
                raise RuntimeError(f"Bad comfy flow or wizard flow, node with id=`{k}` can not be found.")
            node["inputs"][k_v["dest_field_name"]] = f"{request_id}_{i}"
    return r


def execute_comfy_flow(comfy_flow: dict, client_id: str) -> dict:
    r = httpx.post(f"http://127.0.0.1:{options.COMFY_PORT}/prompt", json={"prompt": comfy_flow, "client_id": client_id})
    if r.status_code != 200:
        raise RuntimeError(f"ComfyUI returned status: {r.status_code}")
    return json.loads(r.text)


def open_comfy_websocket(request_id: str):
    return connect(f"ws://127.0.0.1:{options.COMFY_PORT}/ws?clientId={request_id}")
