import builtins
import hashlib
import logging
import os
import typing
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import status

from . import options
from .pydantic_models import AIResourceModel

DOWNLOAD_RETRY_COUNT = 3
LOGGER = logging.getLogger("visionatrix")


def install_model(
    model: AIResourceModel,
    flow_name: str,
    progress_for_model: float,
    progress_callback: typing.Callable[[str, float, str, bool], bool] | None = None,
    hf_auth_token: str = "",
) -> bool:
    model.hash = model.hash.lower()
    if str(model.save_path).find("{root}") != -1:
        save_path = Path(options.BACKEND_DIR).joinpath(model.save_path.replace("{root}", ""))
    else:
        save_path = Path(options.MODELS_DIR).joinpath(model.save_path)
    LOGGER.debug("model=%s --> save_path=%s", model.name, save_path)
    check_result = False
    if save_path.exists() and not model.url.endswith(".zip"):
        if check_hash(model.hash, save_path):
            LOGGER.info("`%s` already exists.", save_path)
            check_result = True
        else:
            LOGGER.warning("Model `%s` exists but has invalid hash. Reinstalling..", model.name)
    elif save_path.suffix == ".zip":
        check_result = True
        if not model.hashes:
            LOGGER.info("`%s` does not provide hashes for files in archive, skipping.", save_path)
        else:
            for model_name, model_hash in model.hashes.items():
                archive_element = Path(save_path.with_suffix("")).joinpath(model_name)
                if archive_element.exists():
                    if check_hash(model_hash, archive_element):
                        LOGGER.info("`%s` already exists.", archive_element)
                        continue
                    LOGGER.warning("Model `%s` exists but has invalid hash. Reinstalling..", archive_element)
                check_result = False
                break

    if check_result is True:
        if progress_callback is None:
            return True
        return progress_callback(flow_name, progress_for_model, "", True)

    os.makedirs(save_path.parent, exist_ok=True)
    for _ in range(DOWNLOAD_RETRY_COUNT):
        LOGGER.info("Downloading `%s`..", model.name)
        try:
            return download_model(model, save_path, flow_name, progress_for_model, progress_callback, hf_auth_token)
        except KeyboardInterrupt:
            save_path.unlink(missing_ok=True)
            LOGGER.warning("Received SIGINT, download terminated")
            raise
        except Exception as e:
            LOGGER.warning("Error during downloading `%s`", model.name, exc_info=e)

    if progress_callback is not None:
        progress_callback(flow_name, 0.0, f"Can not install model from `{model.url}`", False)
        return False
    raise RuntimeError(f"Can not install model from `{model.url}`") from None


def download_model(
    model: AIResourceModel,
    save_path: Path,
    flow_name: str,
    progress_for_model: float,
    progress_callback: typing.Callable[[str, float, str, bool], bool] | None = None,
    hf_auth_token: str = "",
) -> bool:
    if options.VIX_MODE == "SERVER" and options.VIX_SERVER_FULL_MODELS == "0":
        with builtins.open(save_path, "w", encoding="UTF-8") as file:
            file.write("SERVER MODE")
        return True

    headers = {}
    if model.gated and urlparse(model.url).netloc == "huggingface.co" and hf_auth_token:
        headers["Authorization"] = f"Bearer {hf_auth_token}"

    existing_file_size = 0
    if save_path.exists():
        existing_file_size = save_path.stat().st_size
        if existing_file_size > 0:
            headers["Range"] = f"bytes={existing_file_size}-"
            LOGGER.info("Resuming download from byte %d", existing_file_size)

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

            check_etag(response, model)

            if existing_file_size > 0:
                total_added_progress = progress_for_model * existing_file_size / total_size
                if progress_callback is not None:
                    progress_callback(flow_name, total_added_progress, "", True)
            else:
                total_added_progress = 0.0
            progress_value = 0.0

            try:
                mode = "ab" if existing_file_size > 0 else "wb"
                with builtins.open(save_path, mode) as file:
                    for chunk in response.iter_bytes(10 * 1024 * 1024):
                        if chunk:
                            bytes_written = file.write(chunk)
                            if progress_callback is not None:
                                increment = progress_for_model * bytes_written / total_size
                                progress_value += increment
                                if progress_value >= 0.1:
                                    if not progress_callback(flow_name, progress_value, "", True):
                                        LOGGER.warning("Download of '%s' was interrupted.", model.url)
                                        return False
                                    total_added_progress += progress_value
                                    progress_value = 0.0
                if not check_hash(model.hash, save_path):
                    save_path.unlink(missing_ok=True)
                    raise RuntimeError("Downloaded file hash does not match the expected hash.")
            except (httpx.HTTPError, RuntimeError):
                if progress_callback is not None:
                    progress_callback(flow_name, -total_added_progress, "", True)
                raise
            if model.url.endswith(".zip"):
                with zipfile.ZipFile(save_path) as zip_file:
                    zip_file.extractall(save_path.parent)
                os.unlink(save_path)
            return True
    save_path.unlink(missing_ok=True)
    raise RuntimeError("Failed to download model after retries")


def check_hash(etag: str, model_path: str | Path) -> bool:
    if options.VIX_MODE == "SERVER" and options.VIX_SERVER_FULL_MODELS == "0":
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
