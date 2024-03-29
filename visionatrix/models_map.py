import builtins
import json
import logging
import re
from urllib.parse import urlparse

import httpx

from . import options
from .nodes import get_node_value, set_node_value

LOGGER = logging.getLogger("visionatrix")
MODEL_LOAD_CLASSES = {
    "CheckpointLoaderSimple": {
        "1": ["inputs", "ckpt_name"],
    },
    "ControlNetLoader": {
        "1": ["inputs", "control_net_name"],
    },
    "Efficient Loader": {
        "1": ["inputs", "ckpt_name"],
        "2": ["inputs", "lora_name"],
    },
    "InstantIDModelLoader": {"1": ["inputs", "instantid_file"]},
    "LoraLoader": {"1": ["inputs", "lora_name"]},
    "LoraLoaderModelOnly": {"1": ["inputs", "lora_name"]},
    "PhotoMakerLoader": {"1": ["inputs", "photomaker_model_name"]},
    "VAELoader": {"1": ["inputs", "vae_name"]},
    "UpscaleModelLoader": {"1": ["inputs", "model_name"]},
}
MODELS_CATALOG: dict[str, dict] = {}


def fill_flow_models_from_comfy_flow(flow: dict, flow_comfy: dict[str, dict]) -> None:
    if "models" in flow:
        return
    models_catalog = get_models_catalog()
    models_info = []
    for node_details in flow_comfy.values():
        if (load_class := MODEL_LOAD_CLASSES.get(node_details.get("class_type"))) is None:
            continue
        for node_model_load_path in load_class.values():
            node_input_model_name = get_node_value(node_details, node_model_load_path)
            not_found = True
            for model, model_details in models_catalog.items():
                if match_replace_model(model_details, node_input_model_name, node_details, node_model_load_path):
                    if model not in [i["name"] for i in models_info]:
                        model_info = model_details.copy()
                        model_info.pop("regexes")
                        model_info["name"] = model
                        models_info.append(model_info)
                    not_found = False
                    break
            if not_found:
                LOGGER.error("Can not map model for:\n%s", node_details)
    flow["models"] = models_info


def match_replace_model(
    model_details: dict,
    node_input_model_name: str,
    node_details: dict,
    node_model_load_path: list[str],
) -> bool:
    for regex in model_details["regexes"]:
        _input_value = "input_value" not in regex or re.match(regex["input_value"], node_input_model_name) is not None
        _input_name = "input_name" not in regex or re.match(regex["input_name"], node_model_load_path[-1]) is not None
        _class_name = "class_name" not in regex or re.match(regex["class_name"], node_details["class_type"]) is not None
        if _input_value and _input_name and _class_name:
            set_node_value(
                node_details,
                node_model_load_path,
                skip_first_part_of_path(model_details["save_path"]),
            )
            return True
    return False


def skip_first_part_of_path(save_path: str):
    parts = save_path.split("/", 1)
    return parts[1] if len(parts) > 1 else save_path


def get_models_catalog() -> dict[str, dict]:
    if not MODELS_CATALOG:
        if urlparse(options.MODELS_CATALOG_URL).scheme in ("http", "https", "ftp", "ftps"):
            MODELS_CATALOG.update(json.loads(httpx.get(options.MODELS_CATALOG_URL).text))
        else:
            with builtins.open(options.MODELS_CATALOG_URL, encoding="UTF-8") as models_catalog_file:
                MODELS_CATALOG.update(json.loads(models_catalog_file.read()))
    return MODELS_CATALOG
