import subprocess
import os
import sys
from pathlib import Path
from shutil import rmtree


def clone_repository() -> None:
    try:
        subprocess.check_call(["git", "clone", "https://github.com/cloud-media-flows/ai_media_wizard.git"])
        print("Repository cloned successfully.")
    except subprocess.CalledProcessError as e:
        print("An error occurred while trying to clone the repository:", str(e))
        raise
    except Exception as e:
        if e.__class__ == FileNotFoundError:
            print("git command could not be found. Please ensure Git is installed and added to your PATH.")
        else:
            print("An unexpected error occurred:", str(e))
        raise


def create_venv() -> None:
    try:
        subprocess.check_call([sys.executable, "-m", "venv", "venv"], cwd="ai_media_wizard")
        print("Virtual environment created successfully.")
    except Exception as e:
        print("An error occurred while creating the virtual environment:", str(e))
        raise


def venv_run(command: str) -> None:
    if sys.platform.lower() == "win32":
        command = f"call venv/Scripts/activate.bat && {command}"
    else:
        command = f". venv/bin/activate && {command}"
    try:
        print(f"executing(pwf={os.getcwd()}): {command}")
        subprocess.check_call(command, cwd="ai_media_wizard", shell=True)
    except subprocess.CalledProcessError as e:
        print("An error occurred while executing command in venv:", str(e))
        raise


def install_graphics_card_packages():
    if sys.platform.lower() == "darwin":
        return
    q = "Do you want to install packages for an AMD or NVIDIA graphics card? Enter AMD, NVIDIA, or skip(default): "
    choice = input(q).lower()
    if choice == "amd":
        print("Installing packages for AMD graphics card...")
        if sys.platform.lower() == "win32":
            venv_run("pip install -U torch-directml")
        else:
            venv_run(
                "pip install -U --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/rocm6.0"
            )
    elif choice == "nvidia":
        print("Installing packages for NVIDIA graphics card...")
        venv_run("pip install -U torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121")
    else:
        print("Skipping graphics card package installation.")


if __name__ == "__main__":
    print()
    print("Greetings from Media-Wizard easy install script")
    print()
    print()
    if Path("ai_media_wizard").exists():
        c = input("ai_media_wizard folder already exists. Remove it? (Y/N): ").lower()
        if c == "y":
            rmtree("ai_media_wizard")
            print("Removed `ai_media_wizard` folder.")
    if not Path("ai_media_wizard").exists():
        clone_repository()
    if Path("ai_media_wizard/venv").exists():
        c = input("ai_media_wizard/venv folder already exists. Remove it? (Y/N): ").lower()
        if c == "y":
            rmtree("ai_media_wizard/venv")
            print("Removed `ai_media_wizard/venv` folder.")
    if not Path("ai_media_wizard/venv").exists():
        create_venv()
    install_graphics_card_packages()
    print("Installing AI-Media-Wizard")
    venv_run('pip install ".[app]"')
    dirs_to_remove = []
    for i in ("amw_flows", "amw_models", "amw_backend"):
        if Path(f"ai_media_wizard/{i}").exists():
            dirs_to_remove.append(f"ai_media_wizard/{i}")
    if dirs_to_remove:
        c = input(f"Next directories will be removed: {dirs_to_remove} Proceed? (Y/N): ").lower()
        if c != "y":
            print("Install aborted by user")
            sys.exit()
    print("Preparing AI-Media-Wizard working instance..")
    venv_run("python -m ai_media_wizard install")
    c = input("Basic installation finished. Run MediaWizard? (Y/N): ").lower()
    if c == "y":
        venv_run("python -m ai_media_wizard run --ui=client")
    else:
        print("You can run in manually later. From activated virtual environment execute:")
        print("python -m ai_media_wizard run --ui=client")
