from datetime import datetime
from pathlib import Path

from . import options
from .flows import get_available_flows, get_installed_flows
from .models_map import get_formatted_models_catalog
from .pydantic_models import OrphanModel


def get_orphan_models() -> list[OrphanModel]:
    """
    Returns a list of OrphanModel objects representing files in the filesystem that do not belong to installed flows.

    This function scans the filesystem under `options.MODELS_DIR` and compares each file
    with the list of required models obtained from installed flows. Models that are not
    present in the installed flows metadata (based on the 'save_path') are considered orphaned.

    Returns:
        A list of OrphanModel instances with information about orphaned files.
    """
    installed_flows = get_installed_flows()
    available_flows = get_available_flows()
    all_known_flows = available_flows | installed_flows

    required_models = {}
    for flow in installed_flows.values():
        for model in flow.models:
            if not model.save_path.startswith("{"):  # Skip if save_path starts with "{"
                required_models[str(Path(model.save_path))] = model

    all_known_models = {str(Path(i.save_path)): i for i in get_formatted_models_catalog()}
    models_to_flows_map = {}
    for flow in all_known_flows.values():
        for model in flow.models:
            if not model.save_path.startswith("{"):  # Skip if save_path starts with "{"
                model_save_path = str(Path(model.save_path))
                if model_save_path in models_to_flows_map:
                    models_to_flows_map[model_save_path].append(flow)
                else:
                    models_to_flows_map[model_save_path] = [flow]
                all_known_models[model_save_path] = model

    orphan_models = []
    ignore_filenames = [".DS_Store"]
    models_dir = Path(options.MODELS_DIR)
    for file_path in models_dir.rglob("*"):
        if file_path.is_file() and file_path.name not in ignore_filenames:
            relative_path = str(file_path.relative_to(models_dir))
            if relative_path not in required_models:
                size_in_mb = file_path.stat().st_size / (1024 * 1024 * 1024)
                creation_time = file_path.stat().st_ctime
                used_in_flows = models_to_flows_map.get(relative_path, [])
                orphan_models.append(
                    OrphanModel(
                        path=relative_path,
                        size=size_in_mb,
                        creation_time=creation_time,
                        res_model=all_known_models.get(relative_path),
                        possible_flows=used_in_flows,
                    )
                )
    return orphan_models


def process_orphan_models(dry_run: bool, no_confirm: bool, include_useful_models: bool):
    orphan_models = get_orphan_models()
    if not include_useful_models:
        orphan_models = [model for model in orphan_models if not model.possible_flows]

    total_size = 0
    for i in orphan_models:
        total_size += i.size

    print(f"Models directory: {options.MODELS_DIR}")
    print(f"Total count of orphan models: {len(orphan_models)}")
    print(f"Total size of orphaned models: {total_size:.1f} GB")

    if dry_run:
        print("\nDry Run Mode: The following files would be deleted:")
    elif no_confirm:
        print("\nNo Confirmation Mode: Deleting orphan models:")

    for orphan in orphan_models:
        creation_time_utc = datetime.utcfromtimestamp(orphan.creation_time).strftime("%Y-%m-%d %H:%M")
        print(f"- {orphan.path} ({orphan.size:.1f} GB)")
        print(f"    File creation time(UTC): {creation_time_utc}")
        if include_useful_models:
            print(f"    Can be used in flows: {[i.name for i in orphan.possible_flows]}")

        if dry_run:
            continue
        if no_confirm:
            file_to_remove = Path(options.MODELS_DIR).joinpath(orphan.path)
            try:
                file_to_remove.unlink()
                print(f"Deleted: {orphan.path}")
            except Exception as e:
                print(f"Error deleting {orphan.path}: {e}")
        else:
            user_input = input(f"Delete {orphan.path}? (y/Y to confirm, any other key to skip): ").lower()
            if user_input == "y":
                file_to_remove = Path(options.MODELS_DIR).joinpath(orphan.path)
                try:
                    file_to_remove.unlink()
                    print(f"Deleted: {orphan.path}")
                except Exception as e:
                    print(f"Error deleting {orphan.path}: {e}")
            else:
                print(f"Skipped: {orphan.path}")

    if dry_run:
        print("\nNo files were actually deleted. (Dry Run Mode)")
