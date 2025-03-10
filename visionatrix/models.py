import asyncio
import builtins
import hashlib
import logging
import math
import os
import re
import time
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
    auth_tokens: tuple[str, str] = ("", ""),  # (huggingface_token, civitai_token)
) -> bool:
    return asyncio.run(__install_model(model, flow_name, auth_tokens))


async def __install_model(
    model: AIResourceModel,
    flow_name: str,
    auth_tokens: tuple[str, str] = ("", ""),  # (huggingface_token, civitai_token)
) -> bool:
    model.hash = model.hash.lower()
    max_retries = 3
    retries = 0

    # We need this part of code to be able to detect models that present on FS but not in Database
    if await does_model_exist_in_fs(
        model, flow_name, (await db_queries.get_installed_models()).get(model.name), delete_invalid=False
    ):
        return True

    while retries < max_retries:
        installed_models = await db_queries.get_installed_models()
        if model.name in installed_models and await does_model_exist_in_fs(
            model, flow_name, installed_models[model.name]
        ):
            return True

        installing_models = await db_queries.models_installation_in_progress(model.name)
        if not installing_models:
            # No other process is installing the model
            await db_queries.delete_old_model_progress_install(model.name)
            if await db_queries.add_model_progress_install(model.name, flow_name):
                break
            retries += 1
            continue

        # Another thread/process is installing the model
        while True:
            installing_models = await db_queries.models_installation_in_progress(model.name)
            if not installing_models:
                # Installation finished, check if the model was installed successfully
                installed_models = await db_queries.get_installed_models()
                if model.name in installed_models and await does_model_exist_in_fs(
                    model, flow_name, installed_models[model.name]
                ):
                    return True
                retries += 1
                await asyncio.sleep(0.5)
                break
            await asyncio.sleep(1.5)
            if not await db_queries.update_flow_updated_at(flow_name):
                return False
        continue

    if retries >= max_retries:
        LOGGER.error("Failed to acquire lock to install `%s` model for `%s` flow.", model.name, flow_name)
        await db_queries.set_flow_progress_install_error(
            flow_name, f"Failed to acquire lock to install `{model.name}` model."
        )
        return False

    # Proceed to install the model
    save_directory, save_name = get_possible_paths_for_model(model)[0]
    save_path = save_directory.joinpath(save_name)
    os.makedirs(save_path.parent, exist_ok=True)
    for _ in range(DOWNLOAD_RETRY_COUNT):
        LOGGER.info("Downloading `%s`..", model.name)
        try:
            if not await db_queries.update_model_progress_install(model.name, flow_name, 0.0):
                await db_queries.set_flow_progress_install_error(
                    flow_name, f"Failed to update progress for model `{model.name}`"
                )
                return False
            r = await download_model(model, save_path, save_name, flow_name, auth_tokens)
            if not r:
                await db_queries.set_model_progress_install_error(model.name, flow_name, "installation was canceled")
                await db_queries.set_flow_progress_install_error(
                    flow_name, f"Model `{model.name}` installation was canceled."
                )
                return False
            return True
        except KeyboardInterrupt:
            save_path.unlink(missing_ok=True)
            error_string = "Received SIGINT, download terminated"
            LOGGER.warning(error_string)
            await db_queries.set_model_progress_install_error(model.name, flow_name, error_string)
            await db_queries.set_flow_progress_install_error(flow_name, error_string)
            raise
        except (FileNotFoundError, PermissionError) as e:
            LOGGER.error("Error during downloading `%s`: %s", model.name, str(e))
            break
        except Exception as e:
            LOGGER.warning("Error during downloading `%s`: %s", model.name, str(e))

    await db_queries.set_model_progress_install_error(model.name, flow_name, "Cannot download model")
    await db_queries.set_flow_progress_install_error(flow_name, f"Cannot download model from `{model.url}`")
    LOGGER.error("Cannot download model from `%s`", model.url)
    return False


async def download_model(
    model: AIResourceModel,
    save_path: Path,
    save_name: str,
    flow_name: str,
    auth_tokens: tuple[str, str] = ("", ""),
) -> bool:
    if options.VIX_MODE == "SERVER" and options.VIX_SERVER_FULL_MODELS == "0" and save_path.suffix != ".zip":
        server_mode_ensure_model_exists(save_path)
        await db_queries.update_model_progress_install(model.name, flow_name, 100.0)
        return True

    headers, existing_file_size = prepare_download_headers(model, save_path, auth_tokens)

    should_retry = True
    while should_retry:
        should_retry = False
        async with httpx.AsyncClient(timeout=15.0) as client:
            async with client.stream("GET", model.url, headers=headers, follow_redirects=True) as response:
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
                            async with httpx.AsyncClient(timeout=15.0) as client_civitai:
                                response_civitai = await client_civitai.get(civitai_search_url)
                                if response_civitai.status_code == status.HTTP_200_OK:
                                    civitai_data = response_civitai.json()
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
                            raise FileNotFoundError(
                                "Resource not found on Hugging Face, and Civitai lookup failed."
                            ) from e
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
                if existing_file_size > 0:
                    # Report initial progress based on existing file size
                    model_progress_percentage = existing_file_size / total_size * 100.0
                    if not await db_queries.update_model_progress_install(
                        model.name, flow_name, model_progress_percentage
                    ):
                        return False

                current_file_size = existing_file_size
                mode = "ab" if existing_file_size > 0 else "wb"
                with builtins.open(save_path, mode) as file:
                    last_reported_progress = existing_file_size / total_size * 100.0
                    last_flow_update = time.monotonic()
                    async for chunk in response.aiter_bytes(10 * 1024 * 1024):
                        if chunk:
                            bytes_written = file.write(chunk)
                            current_file_size += bytes_written
                            model_progress_percentage = min((current_file_size / total_size) * 100.0, 99.9)
                            if model_progress_percentage - last_reported_progress >= 0.3:
                                if not await db_queries.update_model_progress_install(
                                    model.name, flow_name, model_progress_percentage
                                ):
                                    return False
                                LOGGER.info(
                                    "Model `%s` for flow `%s`: installation: %s",
                                    model.name,
                                    flow_name,
                                    math.floor(model_progress_percentage * 10) / 10,
                                )
                                last_reported_progress = model_progress_percentage
                            if time.monotonic() - last_flow_update >= 1.5:
                                if not await db_queries.update_flow_updated_at(flow_name):
                                    return False
                                last_flow_update = time.monotonic()
                if not check_hash(model.hash, save_path, bool(save_path.suffix == ".zip")):
                    save_path.unlink(missing_ok=True)
                    raise RuntimeError("Downloaded file hash does not match the expected hash.")
                if model.url.endswith(".zip"):
                    extract_zip_with_subfolder(save_path, save_path.parent)
                    save_path.unlink(missing_ok=True)
                else:
                    await db_queries.update_model_mtime(
                        model.name, save_path.stat().st_mtime, flow_name, new_filename=save_name
                    )
                await db_queries.update_model_progress_install(model.name, flow_name, 100.0)
                return True
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


async def does_model_exist_in_fs(
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
                if model_progress_install.filename and await check_model_file(
                    model_directory_path, model_progress_install.filename, model, model_progress_install, flow_name
                ):
                    return True
            if save_path.exists():
                LOGGER.debug(
                    "File for model '%s' exists at '%s', but it's not in the database.",
                    model.name,
                    save_path,
                )
                if await check_model_file(
                    model_directory_path, model_filename, model, model_progress_install, flow_name
                ):
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
                await db_queries.complete_model_progress_install(model.name, flow_name)
                return True

    return await lookup_for_model_file(model, model_possible_directories, flow_name, model_progress_install)


async def check_model_file(
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
                if not await db_queries.add_model_progress_install(model.name, flow_name, model_filename):
                    await db_queries.reset_model_progress_install_error(model.name, flow_name)
            await db_queries.update_model_mtime(
                model.name, model_existing_path.stat().st_mtime, new_filename=model_filename
            )
            await db_queries.update_model_progress_install(model.name, flow_name, 100.0, not_critical=True)
            return True
    return False


async def lookup_for_model_file(
    model: AIResourceModel,
    model_possible_directories: list[Path],
    flow_name: str,
    model_progress_install: ModelProgressInstall | None = None,
) -> bool:
    if not model.regexes:
        return False
    for model_possible_directory in model_possible_directories:
        if await lookup_for_model_file_in_directory(model, model_possible_directory, flow_name, model_progress_install):
            return True
    return False


async def lookup_for_model_file_in_directory(
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
                            await db_queries.add_model_progress_install(model.name, flow_name, model_filename)
                        await db_queries.update_model_mtime(
                            model.name,
                            file_path.stat().st_mtime,
                            flow_name,
                            new_filename=model_filename,
                        )
                        await db_queries.update_model_progress_install(model.name, flow_name, 100.0, not_critical=True)
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
    installed_models = await db_queries.get_installed_models()
    for flow in flows.values():
        for model in flow.models:
            model.installed = model.name in installed_models
    return flows
