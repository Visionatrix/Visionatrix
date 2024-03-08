# AI-Media-Wizard

[![Analysis & Coverage](https://github.com/cloud-media-flows/AI_Media_Wizard/actions/workflows/analysis-coverage.yml/badge.svg)](https://github.com/cloud-media-flows/AI_Media_Wizard/actions/workflows/analysis-coverage.yml)
[![Docs](https://github.com/cloud-media-flows/AI_Media_Wizard/actions/workflows/docs.yml/badge.svg)](https://cloud-media-flows.github.io/AI_Media_Wizard/)

![PythonVersion](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)

**AI-driven** media creation and editing with a friendly UI and a backend API for integration with third-party services.

This platform ensures effortless deployment and management of AI-powered, secure workflows, tailor-made for the efficient processing of images and videos.

> [!NOTE]
> The project is currently in the planning-development stage, first release will arrive soon.

## The main goals of the project are as follows:

1. To automate deployment and installation processes of ComfyUI workflows.
2. To utilize only proven workflows and extensions for handling pictures and videos.
3. To avoid adding anything unnecessary or questionable from a security perspective.
4. To provide a convenient API for external services.
5. To ensure an easy and simple user interface for individual users.

*Main principles are: reliability, safety, and simplicity.*

## Easy installation for home use (**in progress, coming soon**)

Requirements:

- Python `3.10` or higher
- Available `git` command

Download and execute `easy_install.py` script:

```console
wget -qO- https://raw.githubusercontent.com/cloud-media-flows/AI_Media_Wizard/main/scripts/easy_install.py | python -
```

Answer the questions, and then everything should work in most cases.

## Manual installation from repository

**Clone repository:**

```console
git clone https://github.com/cloud-media-flows/ai_media_wizard.git && cd ai_media_wizard
```

**Set up virtual environment:**

```console
python -m venv venv
```

**Activate Virtual Environment:**

_Linux/macOS:_

```console
source venv/bin/activate
```

_Windows:_

```console
.\venv\Scripts\Activate.ps1
```

### Install **PyTorch**:

#### AMD (Linux)

Development version of `PyTorch` is preferred for AMD graphic-cards at this moment:

```console
pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/rocm6.0
```

#### AMD (Windows)

```console
pip install torch-directml
```

#### NVIDIA (Linux, Windows)

Stable version of `PyTorch` is preferred for NVIDIA graphic-cards:

```console
pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121
```

#### macOS

_No action needed :)_

### Install MediaWizard using **pip** from sources:

```console
pip install ".[app]"
```

### Perform **AIMediaWizard** initialization

Execute it as a Python Module with ``install`` command:

```console
python -m ai_media_wizard install
```

### Run **AIMediaWizard**

```console
python -m ai_media_wizard run --ui=client
```

## Support

- ⭐️ Star our work (it really motivates)
- ❗️ Create an Issue or Feature Request (bring to us an excellent idea)
- 💁 Resolve some Issue or create a Pull Request (contribute to this project)
- 🙏 Add a Flow or help us improve documentation in any way.

## More Information

We'll be covering more information on how to use it with third-party services, how to add your own media flow,
or how to use it as a Python package in your application in the documentation that will start appearing soon.
