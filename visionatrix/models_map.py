import builtins
import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from packaging.version import Version

from . import _version, options
from .basic_node_list import BASIC_NODE_LIST
from .comfyui_wrapper import get_folder_names_and_paths, get_node_class_mappings
from .nodes_helpers import get_node_value, set_node_value
from .pydantic_models import AIResourceModel, ModelProgressInstall

LOGGER = logging.getLogger("visionatrix")
MODEL_LOAD_CLASSES = {
    "CheckpointLoaderSimple": {
        "1": {
            "path": ["inputs", "ckpt_name"],
            "type": "checkpoints",
        },
    },
    "ControlNetLoader": {
        "1": {
            "path": ["inputs", "control_net_name"],
            "type": "controlnet",
        },
    },
    "Efficient Loader": {
        "1": {
            "path": ["inputs", "ckpt_name"],
            "type": "checkpoints",
        },
        "2": {
            "path": ["inputs", "lora_name"],
            "type": "loras",
        },
    },
    "InstantIDModelLoader": {
        "1": {
            "path": ["inputs", "instantid_file"],
            "type": "instantid",
        },
    },
    "IPAdapterUnifiedLoader": {
        "1": {
            "path": ["inputs", "preset"],
            "type": ["ipadapter", "clip_vision"],
            "preset": True,
        },
    },
    "LoraLoader": {
        "1": {
            "path": ["inputs", "lora_name"],
            "type": "loras",
        }
    },
    "LoraLoaderModelOnly": {
        "1": {
            "path": ["inputs", "lora_name"],
            "type": "loras",
        },
    },
    "PhotoMakerLoader": {
        "1": {
            "path": ["inputs", "photomaker_model_name"],
            "type": "photomaker",
        },
    },
    "VAELoader": {
        "1": {
            "path": ["inputs", "vae_name"],
            "type": "vae",
        },
    },
    "UpscaleModelLoader": {
        "1": {
            "path": ["inputs", "model_name"],
            "type": "upscale_models",
        },
    },
    "SUPIR_model_loader_v2": {
        "1": {
            "path": ["inputs", "supir_model"],
            "type": "checkpoints",
        },
    },
    "PulidModelLoader": {
        "1": {
            "path": ["inputs", "pulid_file"],
            "type": "pulid",
        },
    },
    "PulidFluxModelLoader": {
        "1": {
            "path": ["inputs", "pulid_file"],
            "type": "pulid",
        }
    },
    "Lora Loader Stack (rgthree)": {
        "1": {
            "path": ["inputs", "lora_01"],
            "type": "loras",
        },
        "2": {
            "path": ["inputs", "lora_02"],
            "type": "loras",
        },
        "3": {
            "path": ["inputs", "lora_03"],
            "type": "loras",
        },
        "4": {
            "path": ["inputs", "lora_04"],
            "type": "loras",
        },
    },
    "UNETLoader": {
        "1": {
            "path": ["inputs", "unet_name"],
            "type": "diffusion_models",
        },
    },
    "CLIPLoader": {
        "1": {
            "path": ["inputs", "clip_name"],
            "type": "text_encoders",
        },
    },
    "DualCLIPLoader": {
        "1": {
            "path": ["inputs", "clip_name1"],
            "type": "text_encoders",
        },
        "2": {
            "path": ["inputs", "clip_name2"],
            "type": "text_encoders",
        },
    },
    "TripleCLIPLoader": {
        "1": {
            "path": ["inputs", "clip_name1"],
            "type": "text_encoders",
        },
        "2": {
            "path": ["inputs", "clip_name2"],
            "type": "text_encoders",
        },
        "3": {
            "path": ["inputs", "clip_name3"],
            "type": "text_encoders",
        },
    },
    "PhotoMakerLoaderPlus": {
        "1": {
            "path": ["inputs", "photomaker_model_name"],
            "type": "photomaker",
        },
    },
    "RIFE VFI": {
        "1": {
            "path": ["inputs", "ckpt_name"],
            "preset": True,
        },
    },
    "DWPreprocessor": {
        "1": {
            "path": ["inputs", "bbox_detector"],
            "preset": True,
        },
        "2": {
            "path": ["inputs", "pose_estimator"],
            "preset": True,
        },
    },
    "LoadRembgByBiRefNetModel": {
        "1": {
            "path": ["inputs", "model"],
            "type": "birefnet",
        },
    },
    "StyleModelLoader": {
        "1": {
            "path": ["inputs", "style_model_name"],
            "type": "style_models",
        },
    },
    "Power Lora Loader (rgthree)": {
        str(i): {
            "path": ["inputs", f"lora_{i}", "lora"],
            "type": "loras",
        }
        for i in range(1, 32)
    },
    "CLIPVisionLoader": {
        "1": {
            "path": ["inputs", "clip_name"],
            "type": "clip_vision",
        },
    },
}
MODELS_CATALOG: dict[str, dict] = {}


def process_flow_models(
    flow_comfy: dict[str, dict], remap_data: dict[str, ModelProgressInstall]
) -> list[AIResourceModel]:
    nodes_with_models = {key: value["models"] for key, value in BASIC_NODE_LIST.items() if value.get("models")}
    nodes_class_mappings = get_node_class_mappings()

    models_catalog = get_united_model_catalog(flow_comfy)
    simple_model_load_classes = get_simple_model_load_classes(models_catalog)
    models_info: list[AIResourceModel] = []
    for node_details in flow_comfy.values():
        class_type = node_details.get("class_type")
        node_class_mapping = nodes_class_mappings.get(class_type)
        if node_class_mapping and hasattr(node_class_mapping, "RELATIVE_PYTHON_MODULE"):
            node_module = str(node_class_mapping.RELATIVE_PYTHON_MODULE).rsplit(".", 1)[-1]
            models_from_nodes = nodes_with_models.get(node_module, [])
            for node_model_info in models_from_nodes:
                if node_model_info.name not in [i.name for i in models_info]:
                    models_info.append(node_model_info)

        simple_loader = False
        for i, v in simple_model_load_classes.items():
            if re.match(i, class_type) is not None:
                simple_loader_class_model_name = v
                if simple_loader_class_model_name not in [i.name for i in models_info]:
                    models_info.append(
                        AIResourceModel(
                            **models_catalog[simple_loader_class_model_name],
                            name=simple_loader_class_model_name,
                        )
                    )
                simple_loader = True
        if simple_loader:
            continue

        if (load_class := MODEL_LOAD_CLASSES.get(class_type)) is None:
            continue
        for k, node_model_load_info in load_class.items():
            node_input_model_name = get_node_value(node_details, node_model_load_info["path"])
            if node_input_model_name in (None, "None"):
                continue
            not_found = True
            for model, model_details in models_catalog.items():
                model_types = model_details.get("types")
                node_model_type = node_model_load_info.get("type")
                if model_types and node_model_type:
                    if isinstance(node_model_type, str):
                        if node_model_type not in model_types:
                            continue
                    elif isinstance(node_model_type, list) and not any(
                        ntype in model_types for ntype in node_model_type
                    ):
                        continue
                if match_replace_model(
                    model, model_details, node_input_model_name, node_details, node_model_load_info, remap_data
                ):
                    if model not in [i.name for i in models_info]:
                        models_info.append(AIResourceModel(**model_details, name=model))
                    not_found = False
            if not_found:
                LOGGER.error("Cannot map model(%s) for %s(%s):\n%s", node_input_model_name, class_type, k, node_details)
    return models_info


def get_united_model_catalog(flow_comfy: dict[str, dict]) -> dict[str, dict]:
    models_catalog = get_models_catalog().copy()
    embedded_models_catalog = get_embedded_models_catalog(flow_comfy)
    for model_name, model_details in embedded_models_catalog.items():
        models_catalog[model_name] = model_details
    return models_catalog


def match_replace_model(
    model: str,
    model_details: dict,
    node_input_model_name: str,
    node_details: dict,
    node_model_load_info: dict[str, str | list[str] | bool],
    remap_data: dict[str, ModelProgressInstall],
) -> bool:
    for regex in model_details["regexes"]:
        node_model_load_path = node_model_load_info["path"]
        _input_value = "input_value" not in regex or re.match(regex["input_value"], node_input_model_name) is not None
        _input_name = "input_name" not in regex or re.match(regex["input_name"], node_model_load_path[-1]) is not None
        _class_name = "class_name" not in regex or re.match(regex["class_name"], node_details["class_type"]) is not None
        if _input_value and _input_name and _class_name:
            if node_model_load_info.get("preset"):
                return True
            if remap_data:
                if model not in remap_data:
                    LOGGER.error("Model `%s` is not marked as installed; mapping may be broken.", model)
                if model in remap_data and remap_data[model].filename:
                    model_filename = remap_data[model].filename
                elif model_details.get("filename"):
                    model_filename = model_details["filename"]
                else:
                    model_filename = urlparse(model_details["url"]).path.split("/")[-1]
                set_node_value(
                    node_details,
                    node_model_load_path,
                    model_filename,
                )
            return True
    return False


def fetch_models_catalog_from_url_or_path(catalog_url: str) -> dict[str, dict]:
    if catalog_url.endswith("/"):
        vix_version = Version(_version.__version__)
        if vix_version.is_devrelease:
            catalog_url += "models_catalog.json"
        else:
            catalog_url += f"models_catalog-{vix_version.major}.{vix_version.minor}.json"
    parsed_url = urlparse(catalog_url)
    if parsed_url.scheme in ("http", "https", "ftp", "ftps"):
        try:
            response = httpx.get(catalog_url, timeout=5.0)
            response.raise_for_status()
            return json.loads(response.text)
        except Exception as e:
            LOGGER.error("Failed to fetch the models catalog from %s: %s", catalog_url, str(e))
            return {}
    else:
        try:
            with builtins.open(catalog_url, encoding="UTF-8") as models_catalog_file:
                return json.loads(models_catalog_file.read())
        except Exception as e:
            LOGGER.error("Failed to read models catalog at %s: %s", catalog_url, str(e))
            return {}


def get_models_catalog() -> dict[str, dict]:
    if not MODELS_CATALOG:
        models_catalog_urls = [url.strip() for url in options.MODELS_CATALOG_URL.split(";") if url.strip()]
        for catalog_url in models_catalog_urls:
            catalog_data = fetch_models_catalog_from_url_or_path(catalog_url)
            for model_name, model_details in catalog_data.items():
                MODELS_CATALOG[model_name] = model_details
    return MODELS_CATALOG


def get_formatted_models_catalog() -> list[AIResourceModel]:
    r = []
    for model, model_details in get_models_catalog().items():
        r.append(AIResourceModel(**model_details, name=model))
    return r


def get_possible_paths_for_model(model: AIResourceModel) -> list[(Path, str)]:
    if not model.types:
        # this is a custom node model that does not support ComfyUI path configuration.
        return [(Path(options.COMFYUI_DIR), model.filename)]

    comfyui_models_paths = get_folder_names_and_paths()
    comfyui_folders_info = None

    for model_type in model.types:
        if model_type in comfyui_models_paths:
            comfyui_folders_info = comfyui_models_paths[model_type]
            break

    if comfyui_folders_info is None:
        raise ValueError(
            f"Error installing model '{model.name}': no directory found for any of the types: {model.types}\n"
            "Please add any of these paths to the file 'ComfyUI/extra_model_paths.yaml'."
        ) from None

    if not comfyui_folders_info[0]:
        raise ValueError(
            f"Error installing model '{model.name}': no output folders found: {comfyui_folders_info}"
        ) from None

    model_filename = model.filename if model.filename else urlparse(model.url).path.split("/")[-1]

    save_paths = []
    for output_folder in comfyui_folders_info[0]:
        save_paths.append(Path(output_folder))
    return [(i, model_filename) for i in save_paths]


def get_possible_final_paths_for_model(
    installed_models: dict[str, ModelProgressInstall], model: AIResourceModel
) -> list[Path]:
    model_filename = model.filename if model.filename else urlparse(model.url).path.split("/")[-1]
    alternative_model_filename = ""
    if model.name in installed_models:
        alternative_model_filename = installed_models[model.name].filename
    if alternative_model_filename and alternative_model_filename != model_filename:
        r = []
        for x, y in get_possible_paths_for_model(model):
            r.append(x.joinpath(y))
            r.append(x.joinpath(alternative_model_filename))
        return r
    return [x.joinpath(y) for x, y in get_possible_paths_for_model(model)]


def get_simple_model_load_classes(models_catalog: dict[str, dict]) -> dict[str, str]:
    """
    There are classes of nodes that are tightly tied to models, without the ability to change or select them.
    In the model catalog such records only have a "class_name" without an "input_value" or "input_name".

    Returns a dictionary with regular expressions to determine by "class_type" whether the node is a simple loader.
    """
    simple_load_classes = {}
    for model_name, model_details in models_catalog.items():
        if "regexes" in model_details:
            simple_loader = True
            for i in model_details["regexes"]:
                if len(i.keys()) != 1 or "class_name" not in i:
                    simple_loader = False
                    break
            if not simple_loader:
                continue
            for i in model_details["regexes"]:
                simple_load_classes[i["class_name"]] = model_name
    return simple_load_classes


def get_embedded_models_catalog(flow_comfy: dict[str, dict]) -> dict[str, dict]:
    for node_details in flow_comfy.values():
        if node_details.get("_meta", {}).get("title", "") == "WF_MODELS":  # Text Multiline (Code Compatible)
            return json.loads(node_details["inputs"]["text"])
    return {}
