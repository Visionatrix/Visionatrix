import builtins
import hashlib
import logging
import os
import re
import time
import typing
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import status

from . import db_queries, options
from .models_map import get_possible_paths_for_model
from .pydantic_models import AIResourceModel, Flow, ModelProgressInstall

DOWNLOAD_RETRY_COUNT = 3
LOGGER = logging.getLogger("visionatrix")


def install_model(
    model: AIResourceModel,
    flow_name: str,
    progress_for_model: float,
    progress_callback: typing.Callable[[str, float, str, bool], bool],
    auth_tokens: tuple[str, str] = ("", ""),  # (huggingface_token, civitai_token)
) -> bool:
    model.hash = model.hash.lower()
    max_retries = 3
    retries = 0

    # We need this part of code to be able to detect models that present on FS but not in Database
    if does_model_exist_in_fs(
        model, flow_name, db_queries.get_installed_models().get(model.name), delete_invalid=False
    ):
        return progress_callback(flow_name, progress_for_model, "", True)

    while retries < max_retries:
        installed_models = db_queries.get_installed_models()
        if model.name in installed_models and does_model_exist_in_fs(model, flow_name, installed_models[model.name]):
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
                if model.name in installed_models and does_model_exist_in_fs(
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
    save_directory, save_name = get_possible_paths_for_model(model)[0]
    save_path = save_directory.joinpath(save_name)
    os.makedirs(save_path.parent, exist_ok=True)
    for _ in range(DOWNLOAD_RETRY_COUNT):
        LOGGER.info("Downloading `%s`..", model.name)
        try:
            if not db_queries.update_model_progress_install(model.name, flow_name, 0.0):
                progress_callback(flow_name, 0.0, f"Failed to update progress for model `{model.name}`", False)
                return False
            r = download_model(
                model, save_path, save_name, flow_name, progress_for_model, progress_callback, auth_tokens
            )
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
        except (FileNotFoundError, PermissionError) as e:
            LOGGER.error("Error during downloading `%s`: %s", model.name, str(e))
            break
        except Exception as e:
            LOGGER.warning("Error during downloading `%s`: %s", model.name, str(e))

    db_queries.set_model_progress_install_error(model.name, flow_name, "Cannot download model")
    progress_callback(flow_name, 0.0, f"Cannot download model from `{model.url}`", False)
    return False


def download_model(
    model: AIResourceModel,
    save_path: Path,
    save_name: str,
    flow_name: str,
    progress_for_model: float,
    progress_callback: typing.Callable[[str, float, str, bool], bool],
    auth_tokens: tuple[str, str] = ("", ""),
) -> bool:
    if options.VIX_MODE == "SERVER" and options.VIX_SERVER_FULL_MODELS == "0" and save_path.suffix != ".zip":
        server_mode_ensure_model_exists(save_path)
        db_queries.update_model_progress_install(model.name, flow_name, 100.0)
        return True

    headers, existing_file_size = prepare_download_headers(model, save_path, auth_tokens)

    should_retry = True
    while should_retry:
        should_retry = False
        with httpx.stream("GET", model.url, headers=headers, follow_redirects=True, timeout=15.0) as response:
            if response.status_code == status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE or (
                existing_file_size > 0 and response.status_code == status.HTTP_404_NOT_FOUND
            ):
                # Cannot resume, restart from beginning
                LOGGER.warning("Cannot resume download; restarting from the beginning.")
                existing_file_size = 0
                headers.pop("Range", None)
                save_path.unlink(missing_ok=True)  # Delete the incomplete file
                should_retry = True
                continue
            if response.status_code == status.HTTP_404_NOT_FOUND:
                if urlparse(model.url).netloc == "huggingface.co":
                    LOGGER.warning("Hugging Face URL not found, attempting to locate model on Civitai.")
                    civitai_search_url = f"https://civitai.com/api/v1/model-versions/by-hash/{model.hash}"
                    try:
                        civitai_response = httpx.get(civitai_search_url, timeout=15.0)
                        if civitai_response.status_code == status.HTTP_200_OK:
                            civitai_data = civitai_response.json()
                            if civitai_data.get("files"):
                                civitai_download_url = civitai_data["files"][0].get("downloadUrl", "")
                                if civitai_download_url:
                                    LOGGER.info("Found model on Civitai. Switching to Civitai download URL.")
                                    model.url = civitai_download_url
                                    headers, existing_file_size = prepare_download_headers(
                                        model, save_path, auth_tokens
                                    )
                                    should_retry = True
                                    continue
                    except httpx.HTTPError as e:
                        LOGGER.error("Failed to fetch model metadata from Civitai: %s", str(e))
                        raise FileNotFoundError("Resource not found on Hugging Face, and Civitai lookup failed.") from e
                raise FileNotFoundError(f"Resource not found at {model.url}")
            if response.status_code == status.HTTP_401_UNAUTHORIZED:
                authorization = headers.get("Authorization", "")
                raise PermissionError(f"Denied access for model at {model.url} with token=`{authorization}`")
            if response.status_code == status.HTTP_200_OK and "Range" in headers:
                # Server does not support resuming
                LOGGER.warning("Server does not support resuming; starting download from scratch.")
                existing_file_size = 0
                headers.pop("Range", None)
                save_path.unlink(missing_ok=True)  # Delete the incomplete file
                should_retry = True
                continue
            if httpx.codes.is_error(response.status_code):
                raise RuntimeError(f"Download request failed with status: {response.status_code}")

            total_size = get_model_total_size(response)
            check_etag(response, model)

            # Actual downloading logic starts here
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
                    db_queries.update_model_mtime(
                        model.name, save_path.stat().st_mtime, flow_name, new_filename=save_name
                    )
                db_queries.update_model_progress_install(model.name, flow_name, 100.0)
                return True
            except (httpx.HTTPError, RuntimeError):
                progress_callback(flow_name, -total_added_progress, "", True)
                raise
    save_path.unlink(missing_ok=True)
    raise RuntimeError("Failed to download model after retries")


def get_model_total_size(response: httpx.Response) -> int:
    if response.status_code == status.HTTP_206_PARTIAL_CONTENT:
        content_range = response.headers.get("Content-Range")
        if content_range is None:
            raise RuntimeError("Server did not provide 'Content-Range' header for partial content.")
        total_size = int(content_range.split("/")[-1])
    else:
        total_size = int(response.headers.get("Content-Length", 0))

    if not total_size:
        raise RuntimeError("Received empty response when attempting to download the model.")
    return total_size


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


def prepare_download_headers(model: AIResourceModel, save_path: Path, auth_tokens: tuple[str, str]) -> tuple[dict, int]:
    headers = {}
    if urlparse(model.url).netloc == "huggingface.co":
        if auth_tokens[0]:
            headers["Authorization"] = f"Bearer {auth_tokens[0]}"
        else:
            LOGGER.warning("Downloading `%s` from `%s`: HuggingFace token was not provided.", model.name, model.url)
    elif urlparse(model.url).netloc == "civitai.com":
        if auth_tokens[1]:
            headers["Authorization"] = f"Bearer {auth_tokens[1]}"
        else:
            LOGGER.warning("Downloading `%s` from `%s`: CivitAI API key was not provided.", model.name, model.url)

    existing_file_size = 0
    if save_path.exists():
        existing_file_size = save_path.stat().st_size
        if existing_file_size > 0:
            headers["Range"] = f"bytes={existing_file_size}-"
            LOGGER.info("Resuming download from byte %d", existing_file_size)
    return headers, existing_file_size


def does_model_exist_in_fs(
    model: AIResourceModel,
    flow_name: str,
    model_progress_install: ModelProgressInstall | None = None,
    delete_invalid: bool = True,
) -> bool:
    model_possible_directories = []
    for model_directory_path, model_filename in get_possible_paths_for_model(model):
        save_path = model_directory_path.joinpath(model_filename)
        if save_path.suffix != ".zip" and not model.url.endswith(".zip"):
            model_possible_directories.append(model_directory_path)
        LOGGER.debug("model=%s --> save_path=%s", model.name, save_path)
        if not model.url.endswith(".zip"):
            if model_progress_install:
                LOGGER.debug(
                    "Model `%s` with filename `%s` record is present in the database.",
                    model.name,
                    model_progress_install.filename,
                )
                if model_progress_install.filename and check_model_file(
                    model_directory_path, model_progress_install.filename, model, model_progress_install, flow_name
                ):
                    return True
            if save_path.exists():
                LOGGER.debug(
                    "File for model '%s' exists at '%s', but it's not in the database.",
                    model.name,
                    save_path,
                )
                if check_model_file(model_directory_path, model_filename, model, model_progress_install, flow_name):
                    return True
                if delete_invalid:
                    LOGGER.warning("Model `%s` exists but has invalid hash. Deleting '%s'", model.name, save_path)
            if delete_invalid:
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
                    if delete_invalid:
                        LOGGER.warning(
                            "Model `%s` exists but has invalid hash. Deleting '%s'", archive_element, archive_element
                        )
                        save_path.unlink(missing_ok=True)
                check_result = False
                break
            if check_result:
                return True

    return lookup_for_model_file(model, model_possible_directories, flow_name, model_progress_install)


def check_model_file(
    model_directory: Path,
    model_filename: str,
    model: AIResourceModel,
    model_progress_install: ModelProgressInstall | None,
    flow_name: str,
) -> bool:
    model_existing_path = model_directory.joinpath(model_filename)
    if model_existing_path.exists():
        if model_progress_install:
            if model_filename == model_progress_install.filename:
                if model_existing_path.stat().st_mtime == model_progress_install.file_mtime:
                    LOGGER.info("`%s` already exists, and modification time is fine.", model_existing_path)
                    return True
                LOGGER.info("`%s` already exists, but modification time differs, checking hash...", model_existing_path)
            else:
                LOGGER.warning(
                    "`%s` already exists, but filename from database does not match, checking hash...",
                    model_existing_path,
                )
        if check_hash(model.hash, model_existing_path):
            LOGGER.info("`%s` already exists, and hash is fine.", model_existing_path)
            if options.VIX_MODE == "SERVER" and options.VIX_SERVER_FULL_MODELS == "0":
                return True
            if not model_progress_install:
                LOGGER.debug("Adding model `%s` to the database.", model.name)
                if not db_queries.add_model_progress_install(model.name, flow_name, model_filename):
                    db_queries.reset_model_progress_install_error(model.name, flow_name)
            db_queries.update_model_mtime(model.name, model_existing_path.stat().st_mtime, new_filename=model_filename)
            db_queries.update_model_progress_install(model.name, flow_name, 100.0, not_critical=True)
            return True
    return False


def lookup_for_model_file(
    model: AIResourceModel,
    model_possible_directories: list[Path],
    flow_name: str,
    model_progress_install: ModelProgressInstall | None = None,
) -> bool:
    if not model.regexes:
        return False
    for model_possible_directory in model_possible_directories:
        if lookup_for_model_file_in_directory(model, model_possible_directory, flow_name, model_progress_install):
            return True
    return False


def lookup_for_model_file_in_directory(
    model: AIResourceModel,
    model_possible_directory: Path,
    flow_name: str,
    model_progress_install: ModelProgressInstall | None = None,
) -> bool:
    if not model_possible_directory.exists() or not model_possible_directory.is_dir():
        return False

    for root, _, files in os.walk(model_possible_directory):
        for file_name in files:
            file_path = Path(root) / file_name

            # Check if the file matches any of the regex patterns provided in the model's regexes
            for regex in model.regexes:
                if "input_value" in regex and re.match(regex["input_value"], file_name):
                    LOGGER.info("Found potential match for `%s` at `%s`.", model.name, file_path)

                    # Validate the file hash
                    if check_hash(model.hash, file_path):
                        LOGGER.info("Validated hash for `%s` at `%s`.", model.name, file_path)
                        model_filename = str(file_path.relative_to(model_possible_directory))

                        # Update the database with the model's information
                        if not model_progress_install:
                            db_queries.add_model_progress_install(model.name, flow_name, model_filename)
                        db_queries.update_model_mtime(
                            model.name,
                            file_path.stat().st_mtime,
                            flow_name,
                            new_filename=model_filename,
                        )
                        db_queries.update_model_progress_install(model.name, flow_name, 100.0, not_critical=True)
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
    if linked_etag != model.hash and model.url.find("civitai.com/") == -1 and not model.filename.endswith(".py"):
        raise RuntimeError(f"Model hash mismatch: {linked_etag} != {model.hash}, please report this.")


def server_mode_ensure_model_exists(save_path: Path) -> None:
    if save_path.exists():
        return
    with builtins.open(save_path, "w", encoding="UTF-8") as file:
        file.write("SERVER MODE")


async def fill_flows_model_installed_field(flows: dict[str, Flow]) -> dict[str, Flow]:
    installed_models = db_queries.get_installed_models()
    for flow in flows.values():
        for model in flow.models:
            model.installed = model.name in installed_models
    return flows
