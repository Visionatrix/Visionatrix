import builtins
import hashlib
import logging
import os
import time
import typing
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import status

from . import db_queries, options
from .pydantic_models import AIResourceModel, ModelProgressInstall

DOWNLOAD_RETRY_COUNT = 3
LOGGER = logging.getLogger("visionatrix")


def install_model(
    model: AIResourceModel,
    flow_name: str,
    progress_for_model: float,
    progress_callback: typing.Callable[[str, float, str, bool], bool],
    hf_auth_token: str = "",
) -> bool:
    model.hash = model.hash.lower()
    max_retries = 3
    retries = 0

    # We need this part of code to be able to detect models that present on FS but not in Database
    if is_model_exists_in_fs(model, flow_name, db_queries.get_installed_models().get(model.name)):
        return progress_callback(flow_name, progress_for_model, "", True)

    while retries < max_retries:
        installed_models = db_queries.get_installed_models()
        if model.name in installed_models and is_model_exists_in_fs(model, flow_name, installed_models[model.name]):
            return progress_callback(flow_name, progress_for_model, "", True)

        installing_models = db_queries.models_installation_in_progress(model.name)
        if not installing_models:
            # No other process is installing the model
            db_queries.delete_old_model_progress_install(model.name)
            if db_queries.add_model_progress_install(model.name, flow_name):
                break
            retries += 1
            continue

        # Another thread/process is installing the model
        total_added_progress = 0.0
        previous_model_progress = 0.0
        while True:
            installing_models = db_queries.models_installation_in_progress(model.name)
            if not installing_models:
                # Installation finished, check if the model was installed successfully
                installed_models = db_queries.get_installed_models()
                if model.name in installed_models and is_model_exists_in_fs(
                    model, flow_name, installed_models[model.name]
                ):
                    # Model installed successfully
                    if total_added_progress < progress_for_model:
                        # Add any remaining progress
                        remaining_progress = progress_for_model - total_added_progress
                        progress_callback(flow_name, remaining_progress, "", True)
                    return True

                if total_added_progress > 0 and not progress_callback(flow_name, -total_added_progress, "", True):
                    return False  # Model installation failed; Progress roll back failed
                retries += 1
                time.sleep(0.5)
                break
            model_progress_status = installing_models[model.name]
            new_model_progress = model_progress_status.progress
            new_progress_difference = new_model_progress - previous_model_progress
            flow_progress_increment = (new_progress_difference / 100.0) * progress_for_model

            # Adjust flow_progress_increment to not exceed remaining progress
            remaining_progress = progress_for_model - total_added_progress
            flow_progress_increment = max(min(flow_progress_increment, remaining_progress), -total_added_progress)

            if flow_progress_increment != 0:
                if not progress_callback(flow_name, flow_progress_increment, "", True):
                    return False
                total_added_progress += flow_progress_increment
                previous_model_progress = new_model_progress
            time.sleep(1)
        continue

    if retries >= max_retries:
        LOGGER.error("Failed to acquire lock to install `%s` model for `%s` flow.", model.name, flow_name)
        progress_callback(flow_name, 0.0, f"Failed to acquire lock to install `{model.name}` model.", False)
        return False

    # Proceed to install the model
    save_path = Path(model.paths[0])
    os.makedirs(save_path.parent, exist_ok=True)
    for _ in range(DOWNLOAD_RETRY_COUNT):
        LOGGER.info("Downloading `%s`..", model.name)
        try:
            if not db_queries.update_model_progress_install(model.name, flow_name, 0.0):
                progress_callback(flow_name, 0.0, f"Fail to update progress for model `{model.name}`", False)
                return False
            r = download_model(model, save_path, flow_name, progress_for_model, progress_callback, hf_auth_token)
            if not r:
                db_queries.set_model_progress_install_error(model.name, flow_name, "installation was canceled")
                progress_callback(flow_name, 0.0, f"Model `{model.name}` installation was canceled.", False)
                return False
            return True
        except KeyboardInterrupt:
            save_path.unlink(missing_ok=True)
            error_string = "Received SIGINT, download terminated"
            LOGGER.warning(error_string)
            db_queries.set_model_progress_install_error(model.name, flow_name, error_string)
            progress_callback(flow_name, 0.0, error_string, False)
            raise
        except Exception as e:
            LOGGER.warning("Error during downloading `%s`: %s", model.name, str(e))

    db_queries.set_model_progress_install_error(model.name, flow_name, "Cannot download model")
    progress_callback(flow_name, 0.0, f"Cannot download model from `{model.url}`", False)
    return False


def download_model(
    model: AIResourceModel,
    save_path: Path,
    flow_name: str,
    progress_for_model: float,
    progress_callback: typing.Callable[[str, float, str, bool], bool],
    hf_auth_token: str = "",
) -> bool:
    if options.VIX_MODE == "SERVER" and options.VIX_SERVER_FULL_MODELS == "0" and save_path.suffix != ".zip":
        server_mode_ensure_model_exists(save_path)
        db_queries.update_model_progress_install(model.name, flow_name, 100.0)
        return True

    headers, existing_file_size = prepare_download_headers(model, save_path, hf_auth_token)

    retry = True
    while retry:
        retry = False
        with httpx.stream("GET", model.url, headers=headers, follow_redirects=True, timeout=15.0) as response:
            if response.status_code == status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE or (
                existing_file_size > 0 and response.status_code == status.HTTP_404_NOT_FOUND
            ):
                # Cannot resume, restart from beginning
                LOGGER.warning("Cannot resume download; restarting from the beginning.")
                existing_file_size = 0
                headers.pop("Range", None)
                save_path.unlink(missing_ok=True)  # Delete the incomplete file
                retry = True
                continue
            if response.status_code == status.HTTP_404_NOT_FOUND:
                raise RuntimeError(f"Resource not found at {model.url}")
            if response.status_code == status.HTTP_200_OK and "Range" in headers:
                # Server does not support resuming
                LOGGER.warning("Server does not support resuming; starting download from scratch.")
                existing_file_size = 0
                headers.pop("Range", None)
                save_path.unlink(missing_ok=True)  # Delete the incomplete file
                retry = True
                continue
            if httpx.codes.is_error(response.status_code):
                if response.status_code == status.HTTP_401_UNAUTHORIZED and model.gated:
                    raise RuntimeError(f"Denied access for gated model at {model.url} with token={hf_auth_token}")
                raise RuntimeError(f"Download request failed with status: {response.status_code}")

            # Actual downloading logic starts here
            if response.status_code == status.HTTP_206_PARTIAL_CONTENT:
                content_range = response.headers.get("Content-Range")
                if content_range is None:
                    raise RuntimeError("Server did not provide 'Content-Range' header for partial content.")
                total_size = int(content_range.split("/")[-1])
            else:
                total_size = int(response.headers.get("Content-Length", 0))

            if not total_size:
                raise RuntimeError("Received empty response when attempting to download the model.")
            check_etag(response, model)

            total_added_progress = 0.0  # Total progress added to flow progress
            progress_value = 0.0  # Accumulated progress in flow progress units
            if existing_file_size > 0:
                # Report initial progress based on existing file size
                model_progress_percentage = existing_file_size / total_size * 100.0
                if not db_queries.update_model_progress_install(model.name, flow_name, model_progress_percentage):
                    return False
                # For flow progress, we calculate the proportion of progress_for_model
                total_added_progress = progress_for_model * existing_file_size / total_size
                if not progress_callback(flow_name, total_added_progress, "", True):
                    return False

            current_file_size = existing_file_size
            try:
                mode = "ab" if existing_file_size > 0 else "wb"
                with builtins.open(save_path, mode) as file:
                    for chunk in response.iter_bytes(10 * 1024 * 1024):
                        if chunk:
                            bytes_written = file.write(chunk)
                            current_file_size += bytes_written
                            model_progress_percentage = min((current_file_size / total_size) * 100.0, 99.9)

                            if not db_queries.update_model_progress_install(
                                model.name, flow_name, model_progress_percentage
                            ):
                                return False

                            increment = progress_for_model * bytes_written / total_size
                            progress_value += increment
                            if progress_value >= 0.1:
                                if not progress_callback(flow_name, progress_value, "", True):
                                    return False
                                total_added_progress += progress_value
                                progress_value = 0.0
                if not check_hash(model.hash, save_path, bool(save_path.suffix == ".zip")):
                    save_path.unlink(missing_ok=True)
                    raise RuntimeError("Downloaded file hash does not match the expected hash.")
                if model.url.endswith(".zip"):
                    extract_zip_with_subfolder(save_path, save_path.parent)
                    save_path.unlink(missing_ok=True)
                else:
                    db_queries.update_model_mtime(model.name, save_path.stat().st_mtime, flow_name)
                db_queries.update_model_progress_install(model.name, flow_name, 100.0)
                return True
            except (httpx.HTTPError, RuntimeError):
                progress_callback(flow_name, -total_added_progress, "", True)
                raise
    save_path.unlink(missing_ok=True)
    raise RuntimeError("Failed to download model after retries")


def extract_zip_with_subfolder(zip_path: Path, extract_to: Path):
    with zipfile.ZipFile(zip_path) as zip_file:
        # Get the list of top-level items in the archive
        top_level_items = {os.path.split(item)[0] for item in zip_file.namelist()}

        # Check if all files are in a single top-level folder
        if len(top_level_items) == 1 and "" not in top_level_items:
            # Extract directly if there's a top-level folder
            zip_file.extractall(extract_to)
        else:
            # Create a subfolder based on the archive name
            subfolder_name = zip_path.stem
            subfolder_path = extract_to / subfolder_name
            subfolder_path.mkdir(exist_ok=True)
            zip_file.extractall(subfolder_path)


def prepare_download_headers(model: AIResourceModel, save_path: Path, hf_auth_token: str = "") -> tuple[dict, int]:
    headers = {}
    if model.gated and urlparse(model.url).netloc == "huggingface.co" and hf_auth_token:
        headers["Authorization"] = f"Bearer {hf_auth_token}"
    existing_file_size = 0
    if save_path.exists():
        existing_file_size = save_path.stat().st_size
        if existing_file_size > 0:
            headers["Range"] = f"bytes={existing_file_size}-"
            LOGGER.info("Resuming download from byte %d", existing_file_size)
    return headers, existing_file_size


def is_model_exists_in_fs(
    model: AIResourceModel, flow_name: str, model_progress_install: ModelProgressInstall | None = None
) -> bool:
    for model_paths in model.paths:
        save_path = Path(model_paths)
        LOGGER.debug("model=%s --> save_path=%s", model.name, save_path)
        if save_path.exists() and not model.url.endswith(".zip"):
            if model_progress_install:
                if options.VIX_MODE == "SERVER" and options.VIX_SERVER_FULL_MODELS == "0":
                    return True
                if save_path.stat().st_mtime == model_progress_install.file_mtime:
                    LOGGER.info("`%s` already exists, and modification time is fine.", save_path)
                    return True
                LOGGER.info("`%s` already exists, but modification time differs, checking hash...", save_path)
            if check_hash(model.hash, save_path):
                LOGGER.info("`%s` already exists, and hash is fine.", save_path)
                if options.VIX_MODE == "SERVER" and options.VIX_SERVER_FULL_MODELS == "0":
                    return True
                if model_progress_install:
                    # Model is present in DB, just update the modification time
                    db_queries.update_model_mtime(model.name, save_path.stat().st_mtime)
                elif db_queries.add_model_progress_install(model.name, flow_name):
                    # Model was not present in DB, we successfully added it
                    db_queries.update_model_mtime(model.name, save_path.stat().st_mtime)
                    db_queries.update_model_progress_install(model.name, flow_name, 100.0)
                return True
            LOGGER.warning("Model `%s` exists but has invalid hash. Deleting '%s'", model.name, save_path)
            save_path.unlink(missing_ok=True)
        elif save_path.suffix == ".zip":
            if not model.hashes:
                LOGGER.info("`%s` does not provide hashes for files in archive, skipping.", save_path)
                return True
            check_result = True
            for model_name, model_hash in model.hashes.items():
                archive_element = Path(save_path.with_suffix("")).joinpath(model_name)
                if archive_element.exists():
                    if check_hash(model_hash, archive_element, True):
                        LOGGER.info("`%s` already exists.", archive_element)
                        continue
                    LOGGER.warning(
                        "Model `%s` exists but has invalid hash. Deleting '%s'", archive_element, archive_element
                    )
                    save_path.unlink(missing_ok=True)
                check_result = False
                break
            if check_result:
                return True
    return False


def check_hash(etag: str, model_path: str | Path, force_full_model: bool = False) -> bool:
    if options.VIX_MODE == "SERVER" and options.VIX_SERVER_FULL_MODELS == "0" and force_full_model is False:
        return True
    with builtins.open(model_path, "rb") as file:
        sha256_hash = hashlib.sha256()
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256_hash.update(byte_block)
        return f"{sha256_hash.hexdigest()}" == etag


def check_etag(response: httpx.Response, model: AIResourceModel) -> None:
    linked_etag = ""
    for each_history in response.history:
        linked_etag = each_history.headers.get("X-Linked-ETag", "")
        if linked_etag:
            break
    if not linked_etag:
        linked_etag = response.headers.get("X-Linked-ETag", response.headers.get("ETag", ""))
    linked_etag = linked_etag.strip('"').lower()
    if linked_etag != model.hash and model.url.find("civitai.com/") == -1:
        raise RuntimeError(f"Model hash mismatch: {linked_etag} != {model.hash}, please report this.")


def server_mode_ensure_model_exists(save_path: Path) -> None:
    if save_path.exists():
        return
    with builtins.open(save_path, "w", encoding="UTF-8") as file:
        file.write("SERVER MODE")
