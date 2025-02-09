import json
import re
from urllib.parse import parse_qs, urlparse

import httpx

from . import options
from .db_queries import get_global_setting
from .db_queries_async import get_global_setting_async
from .models_map import (
    get_embedded_models_catalog,
    get_models_catalog,
    get_united_model_catalog,
)
from .nodes_helpers import remove_node_from_comfy_flow
from .pydantic_models import CustomLoraDefinition, LoraConnectionPoint


def add_loras_inputs(
    input_params: list[dict[str, str | list | dict]], loras_connection_points: dict[str, LoraConnectionPoint]
) -> None:
    order_value = 50
    for loras_connection_point in loras_connection_points.values():
        for lora in loras_connection_point.connected_loras:
            input_params.append(
                {
                    "optional": True,
                    "advanced": True,
                    "hidden": False,
                    "translatable": False,
                    "type": "range",
                    "dynamic_lora": True,
                    "order": order_value,
                    "display_name": lora.display_name,
                    "name": "loras_in_param_" + lora.node_id,
                    "default": lora.strength_model,
                    "comfy_node_id": {lora.node_id: ["inputs", "strength_model"]},
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "trigger_words": lora.trigger_words,
                }
            )
            order_value += 1


async def flow_add_model(flow_comfy: dict[str, dict], civitai_model_url: str, types: list[str]) -> [str, list[str]]:
    """
    Adds a new model entry into a ComfyUI flow's embedded WF_MODELS node.

    The key point is to handle:
      - Direct links that already have a '?modelVersionId=XYZ'.
      - Links without '?modelVersionId', e.g. 'https://civitai.com/models/1234/SomeName'
        for which we fetch the model's metadata, pick the *first* version, and proceed.
      - Direct download links like 'https://civitai.com/api/download/models/309330'

    If the model's hash is already in the global catalog or embedded, do nothing.
    Returns model's filename.
    """

    # Early check by URL and return if model is already present in global catalog.
    united_model_catalog = get_models_catalog()
    for existing_val in united_model_catalog.values():
        if existing_val.get("url", "").lower() == civitai_model_url.lower():
            return urlparse(existing_val["url"]).path.split("/")[-1], []

    parsed_url = urlparse(civitai_model_url)
    # For direct download links, extract the model_version_id from the URL path.
    if parsed_url.path.startswith("/api/download/models/"):
        model_version_id = parsed_url.path.split("/")[-1]
    else:
        model_version_id = parse_qs(parsed_url.query).get("modelVersionId", [None])[0]

    if options.VIX_MODE == "SERVER":
        civitai_token = await get_global_setting_async("civitai_auth_token", True)
    else:
        civitai_token = get_global_setting("civitai_auth_token", True)
    headers = {}
    if civitai_token:
        headers["Authorization"] = f"Bearer {civitai_token}"

    # If there's no modelVersionId, parse modelId and fetch the *latest* version
    if not model_version_id:
        match = re.search(r"/models/(\d+)", parsed_url.path)
        if not match:
            # No modelVersionId and no /models/<id> => we cannot proceed
            raise ValueError("CivitAI URL is missing both '?modelVersionId=...' query param and /models/<id> in path.")
        possible_model_id = match.group(1)

        # 1) Fetch the model info from the /models/ endpoint
        model_api_url = f"https://civitai.com/api/v1/models/{possible_model_id}"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(model_api_url, timeout=10, headers=headers)
                r.raise_for_status()
                model_data = r.json()
        except Exception as e:
            raise ValueError(f"Failed to fetch model info from CivitAI: {e}") from e

        versions = model_data.get("modelVersions", [])
        if not versions:
            raise ValueError(f"No versions found for modelId={possible_model_id} on CivitAI.")
        # We'll pick the first version in the array, matching the model_catalog_editor logic
        model_version_id = versions[0].get("id")
        if not model_version_id:
            raise ValueError(f"Cannot extract a valid modelVersionId from /models/{possible_model_id} on CivitAI.")

    # 2) Now we have a model_version_id to fetch
    version_api_url = f"https://civitai.com/api/v1/model-versions/{model_version_id}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(version_api_url, timeout=10, headers=headers)
            r.raise_for_status()
            version_data = r.json()
    except Exception as e:
        raise ValueError(f"Failed to fetch version metadata from CivitAI: {e}") from e

    files = version_data.get("files", [])
    if not files:
        raise ValueError("This version has no files in CivitAI metadata.")
    if len(files) == 1:
        file_info = files[0]
    else:
        file_info = None
        for i in files:
            if i["downloadUrl"] == civitai_model_url:
                file_info = i
                break

    if not file_info:
        raise ValueError("This version has multiple files. Fail to detect what to select. Provide specific file link.")

    sha256 = file_info.get("hashes", {}).get("SHA256")
    if not sha256:
        raise ValueError("No SHA256 hash found for this file in CivitAI metadata.")

    # 3) Avoid duplicates if the model hash is already recognized system-wide
    for existing_val in get_united_model_catalog(flow_comfy).values():
        if existing_val.get("hash", "").lower() == sha256.lower():
            return existing_val.get("filename", urlparse(existing_val["url"]).path.split("/")[-1]), version_data.get(
                "trainedWords", []
            )

    # 4) Build new embedded model entry
    filename = file_info["name"]
    model_id = version_data.get("modelId", "")

    new_entry = {
        "regexes": [{"input_value": rf"(?i)(?:[^\/\\]*[\/\\]?)?{re.escape(filename)}$"}],
        "url": file_info["downloadUrl"],
        "homepage": f"https://civitai.com/models/{model_id}" if model_id else "",
        "hash": sha256.lower(),
        "types": types,
        "filename": filename,
        "file_size": int(file_info["sizeKB"] * 1024),
        "gated": True,
    }

    # 5) Embed into a copy of the flow
    wf_models_node_id = None
    for node_id, node_details in flow_comfy.items():
        if node_details.get("_meta", {}).get("title", "") == "WF_MODELS":
            wf_models_node_id = node_id
            break

    if wf_models_node_id is None:
        wf_models_node_id = str(max(int(k) for k in flow_comfy) + 1)
        flow_comfy[wf_models_node_id] = {
            "inputs": {"text": "{}"},
            "class_type": "Text Multiline (Code Compatible)",
            "_meta": {"title": "WF_MODELS"},
        }

    node_details = flow_comfy[wf_models_node_id]
    embedded_dict = json.loads(node_details["inputs"]["text"])

    # Construct a key for our new model: "CivitAI-<modelId>-<modelVersionId>"
    resolved_model_id = model_id or "unknown"
    key_for_model = f"CivitAI-{resolved_model_id}-{model_version_id}"
    embedded_dict[key_for_model] = new_entry

    node_details["inputs"]["text"] = json.dumps(embedded_dict, indent=2)
    return filename, version_data.get("trainedWords", [])


def flow_remove_model(flow_comfy: dict[str, dict], model_name: str) -> None:
    """Removes a model entry from the embedded WF_MODELS node."""
    wf_node_id = None
    for node_id, node_details in flow_comfy.items():
        if node_details.get("_meta", {}).get("title", "") == "WF_MODELS":
            wf_node_id = node_id
            break
    if wf_node_id is None:
        return

    embedded_catalog = get_embedded_models_catalog(flow_comfy)
    if model_name not in embedded_catalog:
        return

    node_details = flow_comfy[wf_node_id]
    models_dict = json.loads(node_details["inputs"]["text"])
    if model_name not in models_dict:
        return
    del models_dict[model_name]

    if len(models_dict) == 0:
        del flow_comfy[wf_node_id]
    else:
        node_details["inputs"]["text"] = json.dumps(models_dict, indent=2)


def get_flow_lora_connect_points(flow_comfy: dict[str, dict]) -> dict[str, LoraConnectionPoint]:
    """
    Identify all VixDynamicLoraDefinition nodes in the flow, build a LoraConnectionPoint for each, and gather any
    connected LoraLoader nodes as 'connected_loras'.
    """

    lora_points: dict[str, LoraConnectionPoint] = {}
    dynamic_lora_connection_point_nodes = [
        (node_id, node_details)
        for node_id, node_details in flow_comfy.items()
        if node_details.get("class_type") == "VixDynamicLoraDefinition"
    ]
    models_catalog = get_united_model_catalog(flow_comfy)
    for node_id, node_details in dynamic_lora_connection_point_nodes:
        lora_points[node_id] = LoraConnectionPoint(
            description=node_details["inputs"]["description"],
            base_model_type=node_details["inputs"]["base_model_type"],
            connected_loras=get_connected_loras(node_id, flow_comfy, models_catalog),
        )
    return lora_points


def get_connected_loras(
    node_id: str, flow_comfy: dict[str, dict], models_catalog: dict[str, dict]
) -> list[CustomLoraDefinition]:
    """
    BFS from the given 'VixDynamicLoraDefinition' node, collecting all
    reachable 'LoraLoader' nodes (possibly chained) and returning a
    list of fully resolved CustomLoraDefinition objects.

    We only follow edges to child nodes that reference `node_id` in
    any of their inputs. If the child's class_type is:
      - "LoraLoader": we collect it, and continue BFS from there,
      - "VixDynamicLoraDefinition": we skip continuing from that node,
      - anything else: we break that path (do not continue BFS).
    """

    visited: set[str] = set()
    queue: list[str] = [node_id]
    result: list[CustomLoraDefinition] = []

    while queue:
        current = queue.pop(0)
        visited.add(current)

        # Look for children referencing `current`
        for child_id, child_details in flow_comfy.items():
            if child_id in visited:
                continue

            # Check if child references `current` in any of its inputs
            # Typically: child_details["inputs"][some_input] == [current, port_idx]
            inputs_dict: dict = child_details.get("inputs", {})
            if inputs_dict.get("clip", [None])[0] != current or inputs_dict.get("model", [None])[0] != current:
                continue

            if child_details["class_type"] != "LoraLoader":
                visited.add(child_id)

            lora_filename = child_details["inputs"]["lora_name"]
            model_found = create_lora_definition(child_id, lora_filename, models_catalog, child_details)
            if not model_found:
                raise ValueError(f"Cannot map LoRA model({lora_filename}) for node with id={child_id}")

            result.append(model_found)
            visited.add(child_id)
            queue.append(child_id)
    return result


def create_lora_definition(
    child_id: str,
    lora_name: str,
    models_catalog: dict[str, dict],
    child_details: dict,
) -> CustomLoraDefinition | None:
    """
    Finds a fully resolved CustomLoraDefinition for the given lora_name from the united models_catalog,
    if any matches via regexes & type=loras.
    """
    for model_key, model_details in models_catalog.items():
        if "types" not in model_details or "loras" not in model_details["types"]:
            continue

        for rgx in model_details.get("regexes", []):
            if "input_value" in rgx and not re.match(rgx["input_value"], lora_name):
                continue
            if "class_name" in rgx and not re.match(rgx["class_name"], "LoraLoader"):
                continue
            return CustomLoraDefinition(
                **model_details,
                name=model_key,
                strength_model=child_details["inputs"]["strength_model"],
                node_id=child_id,
                display_name=get_ui_input_attribute(child_details, "display_name"),
                trigger_words=json.loads(get_ui_input_attribute(child_details, "trigger_words") or "[]"),
            )
    return None


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


def remove_all_consecutive_loras_for_node(node_id: str, flow_comfy: dict[str, dict]) -> None:
    """
    Removes all consecutive LoRA nodes (i.e., nodes whose _meta['title'] starts with 'lora-input;')
    after 'node_id' in a linear chain, reconnecting the graph so that each child of the removed node
    is linked back to the removed node's parent(s).

    This function repeatedly:
      - Finds the next node referencing 'node_id' in its inputs
      - Checks if its _meta['title'] starts with 'lora-input;'
      - If so, calls remove_node_from_comfy_flow() for that node
      - Continues until no further 'lora-input;' nodes are found in the chain
    """

    # We'll do a loop searching for the next "lora-input;" node in the chain and remove it
    while True:
        # 1) Find any child node referencing 'node_id'
        lora_node_id = None
        for other_id, other_details in flow_comfy.items():
            if other_id == node_id:
                continue
            # Search inputs for reference to 'node_id'
            for _, inp_val in other_details.get("inputs", {}).items():
                if isinstance(inp_val, list) and len(inp_val) == 2 and inp_val[0] == node_id:
                    # Found a child referencing node_id and heck if it's a "lora-input;" node
                    title = other_details.get("_meta", {}).get("title", "")
                    if title.startswith("lora-input;"):
                        lora_node_id = other_id
                        break
            if lora_node_id:
                break

        if not lora_node_id:
            break  # No more child referencing 'node_id' with "lora-input;", we are done

        # 2) Remove that LoRA node from flow
        remove_node_from_comfy_flow(lora_node_id, flow_comfy)


def insert_lora_in_comfy_flow(
    node_id: str,
    display_name: str,
    strength_model: float,
    lora_name: str,
    trigger_words: list[str],
    flow_comfy: dict[str, dict],
) -> str:
    """
    Inserts a new 'LoraLoader' node in the flow *between* the existing 'node_id' and its children.

    The result is a chain:
      [node_id] --(model,clip)--> [new LoRA node] --> [children that used to reference node_id]
    """

    if node_id not in flow_comfy:
        raise ValueError(f"Node '{node_id}' not found in flow.")

    # 1) Allocate a new numeric ID
    existing_ids = [int(k) for k in flow_comfy if k.isdigit()]
    new_id_int = (max(existing_ids) + 1) if existing_ids else 1
    new_node_id = str(new_id_int)

    # 2) Construct the new LoraLoader node referencing node_id
    new_node = {
        "class_type": "LoraLoader",
        "_meta": {"title": f"lora-input;{display_name};trigger_words={json.dumps(trigger_words)}"},
        "inputs": {
            "lora_name": lora_name,
            "strength_model": strength_model,
            "strength_clip": 1,
            "model": [node_id, 0],
            "clip": [node_id, 1],
        },
    }

    flow_comfy[new_node_id] = new_node

    # 3) Find every child that references node_id and redirect them
    #    For each child node:
    #      child_details["inputs"][some_input] == [node_id, port_idx]
    #    we set them to [new_node_id, port_idx] instead.
    for child_id, child_details in flow_comfy.items():
        if child_id in (new_node_id, node_id):
            continue

        for input_name, input_val in child_details.get("inputs", {}).items():
            if isinstance(input_val, list) and len(input_val) == 2 and input_val[0] == node_id:
                # This child references node_id
                # Keep the same port index, just switch to new_node_id
                child_details["inputs"][input_name] = [new_node_id, input_val[1]]

    return new_node_id
