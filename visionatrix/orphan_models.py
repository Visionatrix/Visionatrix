import logging
from datetime import datetime
from pathlib import Path

from . import db_queries, options
from .basic_node_list import BASIC_NODE_LIST
from .comfyui_wrapper import get_folder_names_and_paths
from .flows import get_available_flows, get_installed_flows
from .models_map import get_formatted_models_catalog, get_possible_final_paths_for_model
from .pydantic_models import OrphanModel

LOGGER = logging.getLogger("visionatrix")


def get_orphan_models() -> list[OrphanModel]:
    """
    Returns a list of OrphanModel objects representing files in the filesystem that do not belong to installed flows.

    This function scans the filesystem under ComfyUIs models directory and compares each file
    with the list of required models obtained from installed flows. Models that are not
    present in the installed flows metadata are considered orphaned.

    Returns:
        A list of OrphanModel instances with information about orphaned files.
    """
    installed_flows = get_installed_flows()
    available_flows = get_available_flows()
    all_known_flows = available_flows | installed_flows

    required_models = {}
    for flow in installed_flows.values():
        for model in flow.models:
            for i in get_possible_final_paths_for_model(model):
                required_models[str(i.joinpath())] = model

    all_known_models = {}
    for model in get_formatted_models_catalog():
        for i in get_possible_final_paths_for_model(model):
            all_known_models[str(i)] = model

    models_to_flows_map = {}
    for flow in all_known_flows.values():
        for model in flow.models:
            model_save_paths = {str(i) for i in get_possible_final_paths_for_model(model)}
            for model_save_path in model_save_paths:
                if model_save_path in models_to_flows_map:
                    models_to_flows_map[model_save_path].append(flow)
                else:
                    models_to_flows_map[model_save_path] = [flow]
                all_known_models[model_save_path] = model

    custom_nodes_path = str(Path(options.COMFYUI_DIR).joinpath("custom_nodes"))
    models_filenames_from_nodes = set()
    for node_details in BASIC_NODE_LIST.values():
        if not node_details.get("models"):
            continue
        for model_from_node in node_details["models"]:
            for i in get_possible_final_paths_for_model(model_from_node):
                models_filenames_from_nodes.add(str(i.name))
            for i in model_from_node.hashes:
                models_filenames_from_nodes.add(i)

    orphan_models = set()
    models_extensions = {".bin", ".ckpt", ".pkl", ".pt", ".pth", ".safetensors", ".sft"}
    for path_name, comfyui_models_paths in get_folder_names_and_paths().items():
        if path_name in ("configs", "custom_nodes"):
            continue
        for path_with_models in comfyui_models_paths[0]:
            for file_path in Path(path_with_models).rglob("*"):
                if file_path.is_file() and file_path.suffix in models_extensions:
                    if file_path.name in models_filenames_from_nodes:
                        continue
                    str_file_path = str(file_path)
                    if str_file_path not in required_models and not str_file_path.startswith(custom_nodes_path):
                        size_in_mb = file_path.stat().st_size / (1024 * 1024)
                        creation_time = file_path.stat().st_ctime
                        used_in_flows = models_to_flows_map.get(str_file_path, [])

                        orphan_models.add(
                            OrphanModel(
                                path=str(file_path),
                                full_path=str(Path(file_path).resolve()),
                                size=size_in_mb,
                                creation_time=creation_time,
                                res_model=all_known_models.get(str_file_path),
                                possible_flows=used_in_flows,
                            )
                        )
    return list(orphan_models)


def remove_orphan_model(orphan_path: str) -> bool:
    orphan_file = Path(orphan_path)
    orphan_filename = orphan_file.name
    file_st_ctime = orphan_file.stat().st_ctime
    orphan_file.unlink()
    r = db_queries.delete_model_by_time_and_filename(file_st_ctime, orphan_filename)
    LOGGER.debug("Database removal result for orphan model '%s': %s", orphan_filename, r)
    return bool(r)


def process_orphan_models(dry_run: bool, no_confirm: bool, include_useful_models: bool) -> None:
    if db_queries.models_installation_in_progress():
        print("Some models have the status of being installed. Repeat the request in 3 minutes.")
        return

    orphan_models = get_orphan_models()
    if not include_useful_models:
        orphan_models = [model for model in orphan_models if not model.possible_flows]

    total_size = 0
    for i in orphan_models:
        total_size += i.size

    print(f"Total count of orphan models: {len(orphan_models)}")
    print(f"Total size of orphaned models: {total_size/1024:.2f} GB")

    if dry_run:
        print("\nDry Run Mode: The following files would be deleted:")
    elif no_confirm:
        print("\nNo Confirmation Mode: Deleting orphan models:")

    for orphan in orphan_models:
        creation_time_utc = datetime.utcfromtimestamp(orphan.creation_time).strftime("%Y-%m-%d %H:%M")
        print(f"- {orphan.path} ({orphan.size/1024:.2f} GB)")
        print(f"    Full file path: {orphan.full_path}")
        print(f"    File creation time(UTC): {creation_time_utc}")
        if include_useful_models:
            print(f"    Can be used in flows: {[i.name for i in orphan.possible_flows]}")

        if dry_run:
            continue
        if no_confirm:
            try:
                remove_orphan_model(orphan.path)
                print(f"Deleted: {orphan.path}")
            except Exception as e:
                print(f"Error deleting {orphan.path}: {e}")
        else:
            user_input = input(f"Delete {orphan.path}? (y/Y to confirm, any other key to skip): ").lower()
            if user_input == "y":
                try:
                    remove_orphan_model(orphan.path)
                    print(f"Deleted: {orphan.path}")
                except Exception as e:
                    print(f"Error deleting {orphan.path}: {e}")
            else:
                print(f"Skipped: {orphan.path}")

    if dry_run:
        print("\nNo files were actually deleted. (Dry Run Mode)")
