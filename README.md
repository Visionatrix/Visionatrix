# AI-Media-Wizard
![PythonVersion](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)

**AI-driven** media creation and editing with a friendly UI and a backend API for integration with third-party services.

This platform ensures effortless deployment and management of AI-powered, secure workflows, tailor-made for the efficient processing of images and videos.

> [!NOTE]
> The project is currently in the planning stage.

## The main goals of the project are as follows:

1. To automate deployment and installation processes.
2. To utilize only proven workflows and extensions for handling pictures and videos.
3. To avoid adding anything unnecessary or questionable from a security perspective.
4. To provide a convenient external API for external services.
5. To ensure an easy and simple user interface for individual users.
6. To focus on the use of ComfyUI at this stage.

*Main principles are: reliability, safety, and simplicity.*

## How to install

### Create Project Directory

```console
mkdir ai_media_wizard && cd ai_media_wizard
```

In a case when you wish to join development you can run instead:

```console
git clone https://github.com/cloud-media-flows/ai_media_wizard.git && cd ai_media_wizard
```

### Setting up virtual environment

```console
python -m venv venv
```

### Activation of Virtual Environment

#### Linux/macOS

```console
source env/bin/activate
```

#### Windows:

```console
.\env\Scripts\Activate.ps1
```

### Install **AIMediaWizard**

#### Development version from repository

```console
pip install git+https://github.com/cloud-media-flows/ai_media_wizard.git
```

#### Stable version from [PyPi](https://pypi.org/project/AIMediaWizard/)

```console
pip install ai_media_wizard
```

### Setting Up Hardware Accelerators for Deep Learning

*Currently, install does not differ from installing a [ComfyUI](https://github.com/comfyanonymous/ComfyUI?tab=readme-ov-file#manual-install-windows-linux).*

Install **PyTorch**:

> [!NOTE]
> *Later we have a goal to switch from **PyTorch** to [tinygrad](https://github.com/tinygrad/tinygrad) if it is possible.*

#### AMD

Development version of `PyTorch` is preferred for AMD graphic-cards at this moment:

```console
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/rocm6.0
```

#### NVIDIA

Stable version of `PyTorch` is preferred for NVIDIA graphic-cards:

```console
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121
```

#### macOS

Instructions for `Sonoma` will appear a bit later..

### Perform **AIMediaWizard** initialization

Execute it as a module with ``--init`` command:

```console
python -m ai_media_wizard init
```

#### `init` parameters:

> [!NOTE]
> All parameters have default values, you can override them in a few ways:
>
> 1. Using the ".env" file, that will be read by [dotenv](https://pypi.org/project/python-dotenv/) package.
> 2. Setting them directly in the environment
> 3. Passing them as the arguments to the `--init` command.
> 4. If you use `ai_media_wizard` as the imported package you can specify them during call to the `init` function.

1. `backend_dir` - directory where backend(`ComfyUI`) and all it's extensions will be stored. Default: current working directory **cwd**/backend.
2. `models_dir` - directory where `models` will be stored. Default: **cwd**/models

#### `run` parameters:

1. `interface`
2. `port`
3. `input_directory` - directory where the input data like images will be stored. Default: temp directory/AIMediaWizard/input
4. `output_directory` - directory where the results data like images will be stored. Default: temp directory/AIMediaWizard/output

## Usage

To-do

## Integration in External Service

To-do
