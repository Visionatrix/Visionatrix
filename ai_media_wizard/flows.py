import builtins
import json
import os
from pathlib import Path
from shutil import rmtree
from typing import Any

import httpx
from github import Github, GithubException


def get_available_flows(flows_dir: str, comfy_flows: list | None = None) -> list[dict[str, Any]]:
    repo = Github().get_repo("cloud-media-flows/AI_Media_Wizard")
    installed_flows_ids = [i["name"] for i in get_installed_flows(flows_dir)]
    possible_flows = []
    for flow in repo.get_contents("flows"):
        if flow.type != "dir":
            continue
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
        if flow_data["name"] not in installed_flows_ids:
            possible_flows.append(flow_data)
            if comfy_flows is not None:
                comfy_flows.append(comfy_flow_data)
    return possible_flows


def get_installed_flows(flows_dir: str) -> list[dict[str, Any]]:
    flows = [entry for entry in Path(flows_dir).iterdir() if entry.is_dir()]
    r = []
    for flow in flows:
        if (flow_fp := flow.joinpath("flow.json")).exists() is True:
            r.append(json.loads(flow_fp.read_bytes()))
    return r


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
