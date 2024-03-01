import os
import builtins
from github import Github, GithubException
import json


def init_basic_flows(flows_dir: str):
    repo = Github().get_repo("cloud-media-flows/AI_Media_Wizard")
    basic_flows = repo.get_contents("flows")
    for flow in basic_flows:
        if flow.type != "dir":
            continue
        flow_dir = f"flows/{flow.name}"
        try:
            flow_description = repo.get_contents(f"{flow_dir}/flow.json")
        except GithubException:
            print(f"Can not find `flow.json` for {flow.name}, skipping.")
            continue
        flow_data = json.loads(flow_description.decoded_content)
        comfy_flow = flow_data.get("comfy_flow", "")
        if not comfy_flow:
            print(f"Error, broken flow file: {flow_dir}/flow.json")
            continue
        try:
            comfy_flow_data = repo.get_contents(f"{flow_dir}/{comfy_flow}")
        except GithubException:
            print(f"Can not find `comfy flow` at ({flow_dir}/{comfy_flow}) for {flow.name}, skipping.")
            continue
        local_flow_dir = os.path.join(flows_dir, flow.name)
        os.mkdir(local_flow_dir)
        with builtins.open(os.path.join(local_flow_dir, "flow.json"), mode="wb") as fp:
            fp.write(flow_description.decoded_content)
        with builtins.open(os.path.join(local_flow_dir, comfy_flow), mode="wb") as fp:
            fp.write(comfy_flow_data.decoded_content)
