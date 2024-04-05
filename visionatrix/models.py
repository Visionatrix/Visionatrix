import builtins
import hashlib
import logging
import math
import os
import typing
import zipfile
from pathlib import Path

import httpx

from . import options

DOWNLOAD_RETRY_COUNT = 3
LOGGER = logging.getLogger("visionatrix")


def install_model(
    model: dict[str, str],
    progress_info: dict,
    progress_callback: typing.Callable[[str, float, str], None] | None = None,
) -> bool:
    model["hash"] = model["hash"].lower()
    if str(model["save_path"]).find("{root}") != -1:
        save_path = Path(options.BACKEND_DIR).joinpath(model["save_path"].replace("{root}", ""))
    else:
        save_path = Path(options.MODELS_DIR).joinpath(model["save_path"])
    LOGGER.debug("model=%s --> save_path=%s", model["name"], save_path)
    if save_path.exists() and not model["url"].endswith(".zip"):
        if check_hash(model["hash"], save_path):
            LOGGER.info("`%s` already exists.", save_path)
            if progress_callback is not None:
                progress_info["current"] += progress_info["progress_for_model"]
                progress_info["current"] = math.floor(progress_info["current"] * 10) / 10
                progress_callback(progress_info["name"], progress_info["current"], "")
            return True
        LOGGER.warning("Model `%s` exists but has invalid hash. Reinstalling..", model["name"])

    os.makedirs(save_path.parent, exist_ok=True)
    for _ in range(DOWNLOAD_RETRY_COUNT):
        LOGGER.info("Downloading `%s`..", model["name"])
        if download_model(model, save_path, progress_info, progress_callback):
            if progress_callback is not None:
                progress_info["current"] += progress_info["progress_for_model"]
            return True
    if progress_callback is not None:
        progress_callback(progress_info["name"], 0.0, f"Can not install model from '{model['url']}'")
        return False
    raise RuntimeError(f"Can not install model from '{model['url']}'") from None


def download_model(
    model: dict[str, str],
    save_path: Path,
    progress_info: dict,
    progress_callback: typing.Callable[[str, float, str], None] | None = None,
) -> bool:
    try:
        with httpx.stream("GET", model["url"], follow_redirects=True) as response:
            linked_etag = ""
            for each_history in response.history:
                linked_etag = each_history.headers.get("X-Linked-ETag", "")
                if linked_etag:
                    break
            if not linked_etag:
                linked_etag = response.headers.get("X-Linked-ETag", response.headers.get("ETag", ""))
            linked_etag = linked_etag.strip('"').lower()
            if linked_etag != model["hash"] and model["url"].find("civitai.com/") == -1:
                raise RuntimeError(f"Model hash mismatch: {linked_etag}!={model['hash']}, please, report about this.")
            if not response.is_success:
                raise RuntimeError(f"Downloading of '{model['url']}' returned {response.status_code} status.")
            downloaded_size = 0
            total_size = int(response.headers.get("Content-Length"))
            with builtins.open(save_path, "wb") as file:
                if progress_callback is not None:
                    last_progress_value = math.floor(progress_info["current"] * 10) / 10
                for chunk in response.iter_bytes(10 * 1024 * 1024):
                    downloaded_size += file.write(chunk)
                    if progress_callback is not None:
                        v = progress_info["progress_for_model"] * downloaded_size / total_size
                        new_progress_value = math.floor((progress_info["current"] + v) * 10) / 10
                        if last_progress_value != new_progress_value:
                            progress_callback(progress_info["name"], new_progress_value, "")
                            last_progress_value = new_progress_value
                if not check_hash(model["hash"], save_path):
                    raise RuntimeError(f"Incomplete download of '{model['url']}'.")
            if model["url"].endswith(".zip"):
                with zipfile.ZipFile(save_path) as zip_file:
                    zip_file.extractall(save_path.parent)
                os.unlink(save_path)
            return True
    except Exception as e:
        save_path.unlink(missing_ok=True)
        LOGGER.warning("Error during downloading %s", model["name"], exc_info=e)
        return False
    except KeyboardInterrupt:
        save_path.unlink(missing_ok=True)
        LOGGER.warning("Received SIGINT, download terminated")
        raise


def check_hash(etag: str, model_path: str | Path) -> bool:
    with builtins.open(model_path, "rb") as file:
        sha256_hash = hashlib.sha256()
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256_hash.update(byte_block)
        return f"{sha256_hash.hexdigest()}" == etag
