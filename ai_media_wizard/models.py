import builtins
import hashlib
import os
from pathlib import Path

import httpx

DOWNLOAD_RETRY_COUNT = 3


def install_model(model: dict[str, str], models_dir: str) -> None:
    save_path = Path(models_dir).joinpath(model["save_path"])
    if save_path.exists():
        print(f"`{save_path}` already exists, skipping.")
        return

    os.makedirs(save_path.parent, exist_ok=True)
    for _ in range(DOWNLOAD_RETRY_COUNT):
        if download_model(model, save_path):
            return
    raise RuntimeError(f"Can not install model from '{model['url']}'") from None


def download_model(model: dict[str, str], save_path: Path) -> bool:
    try:
        with httpx.stream("GET", model["url"], follow_redirects=True) as response:
            linked_etag = ""
            for each_history in response.history:
                linked_etag = each_history.headers.get("X-Linked-ETag", "")
                if linked_etag:
                    break
            if not linked_etag:
                linked_etag = response.headers.get("X-Linked-ETag", response.headers.get("ETag", ""))
            linked_etag = linked_etag.strip('"')
            if linked_etag != model["hash"]:
                raise RuntimeError(
                    f"Model at '{model['url']}' has different hash({linked_etag}!={model['hash']}). Please, report"
                    " about this."
                )
            if not response.is_success:
                raise RuntimeError(f"Downloading of '{model['url']}' returned {response.status_code} status.")
            with builtins.open(save_path, "wb") as file:
                for chunk in response.iter_bytes(5 * 1024 * 1024):
                    file.write(chunk)
            with builtins.open(save_path, "rb") as file:
                sha256_hash = hashlib.sha256()
                for byte_block in iter(lambda: file.read(4096), b""):
                    sha256_hash.update(byte_block)
                if f"{sha256_hash.hexdigest()}" != linked_etag:
                    raise RuntimeError(f"Incomplete download of '{model['url']}'.")
            return True
    except Exception as e:  # noqa pylint: disable=broad-exception-caught
        save_path.unlink(missing_ok=True)
        print(e)
        # raise RuntimeError(f"Error during downloading '{model['url']}': {e}") from None
        return False
