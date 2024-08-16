import os
import stat
import subprocess
from pathlib import Path
from shutil import rmtree
from time import sleep

from packaging.version import Version

from visionatrix import _version, install_update  # noqa

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if os.environ.get("CI", False) and not GITHUB_TOKEN:
    raise ValueError("GitHub token is required for CI.")


def tag_repository(repo_name: str, tag_name: str, force_flag: bool = True) -> None:
    local_path = os.path.join("temp_repo_clones", repo_name)

    tag_msg = f"Visionatrix version {tag_name}"
    print(f"Cloning {repo_name}...")
    if GITHUB_TOKEN:
        subprocess.check_call(
            ["git", "clone", f"https://{GITHUB_TOKEN}:x-oauth-basic@github.com/Visionatrix/" + repo_name, local_path]
        )
    else:
        subprocess.check_call(
            ["git", "clone", "https://github.com/Visionatrix/" + repo_name, local_path]
        )
    try:
        print(f"Creating tag {tag_name} in {repo_name}...")
        try:
            subprocess.check_call(["git", "tag", "-a", tag_name, "-m", tag_msg], cwd=local_path)
        except subprocess.CalledProcessError as e:
            if not force_flag:
                raise e
            print(f"{tag_name} already exists in {repo_name}, removing and create new...")
            subprocess.check_call(["git", "tag", "-d", tag_name], cwd=local_path)
            subprocess.check_call(["git", "tag", "-a", tag_name, "-m", tag_msg], cwd=local_path)
        print(f"Pushing tag {tag_name} to {repo_name}...")
        if force_flag:
            subprocess.check_call(["git", "push", "--force", "origin", tag_name], cwd=local_path)
        else:
            subprocess.check_call(["git", "push", "origin", tag_name], cwd=local_path)
        print(f"Tag {tag_name} pushed successfully to {repo_name}.")
    except subprocess.CalledProcessError as e:
        print(f"Error processing {repo_name}: {e}")
        raise e
    finally:
        if os.path.exists(local_path):
            os.system(f"rm -rf {local_path}")  # noqa


def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent.parent)
    visionatrix_version = Version(_version.__version__)
    if visionatrix_version.is_prerelease:
        print("Visionatrix is in a prerelease state. Only Nodes repositories will be tagged.", flush=True)
    sleep(60)

    if os.path.exists("temp_repo_clones"):
        rmtree("temp_repo_clones", onerror=remove_readonly)
    os.mkdir("temp_repo_clones")

    for r in install_update.BASIC_NODE_LIST:
        tag_repository(r, f"v{visionatrix_version.base_version}")

    if visionatrix_version.is_prerelease:
        print("Skipping tagging of Visionatrix repo.", flush=True)
    else:
        tag_repository("Visionatrix", f"v{_version.__version__}")

    print("Tagging process completed.", flush=True)
