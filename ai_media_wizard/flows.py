from typing import Any
from pathlib import Path
import json


def get_all_flows():
    pass  # to-do


def get_installed_flows(flows_dir: str) -> list[dict[str, Any]]:
    flows = [entry for entry in Path(flows_dir).iterdir() if entry.is_dir()]
    r = []
    for flow in flows:
        if (flow_fp := flow.joinpath("flow.json")).exists() is True:
            r.append(json.loads(flow_fp.read_bytes()))
    return r
