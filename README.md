# Visionatrix

[![Analysis & Coverage](https://github.com/Visionatrix/Visionatrix/actions/workflows/analysis-coverage.yml/badge.svg)](https://github.com/Visionatrix/Visionatrix/actions/workflows/analysis-coverage.yml)
[![Documentation](https://github.com/Visionatrix/VixFlowsDocs/actions/workflows/docs.yml/badge.svg)](https://visionatrix.github.io/VixFlowsDocs/)
[![Models Catalog](https://github.com/Visionatrix/VixFlowsDocs/actions/workflows/check-models-catalog.yml/badge.svg)](https://github.com/Visionatrix/VixFlowsDocs/actions/workflows/check-models-catalog.yml)
![PythonVersion](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)

<div align="center">
  <img alt="Visionatrix Logo" height="200px" src="https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/logo.png">
</div>

**Simplify your AI image generation workflows with Visionatrix—an intuitive interface built on top of [ComfyUI](https://github.com/comfyanonymous/ComfyUI)**

## 🚀 Features

- **🔧 Easy Setup & Updates**: Quick setup with simple installation and seamless version updates.
- **🖥️ Minimalistic UI**: Clean, user-friendly interface designed for daily workflow usage.
- **🌐 Prompt Translation Support**: Automatically translate prompts for media generation.
- **🛠️ Stable Workflows**: Versioned and upgradable workflows.
- **📈 Scalability**: Run multiple instances with simultaneous task workers for increased productivity.
- **👥 Multi-User Support**: Configure for multiple users with ease and integrate different user backends.
- **🤖 LLM Integration**: Effortlessly incorporate Ollama/Gemini as your LLM for ComfyUI workflows.
- **🔌 Seamless Integration**: Run as a service with backend endpoints for smooth project integration.
- **😎 LoRA Integration**: Easy integrate LoRAs from CivitAI into your flows.
- **🐳 Docker Compose**: Official Docker images and a pre-configured Docker Compose file.

## 🖼️ User Interface

Access the Visionatrix UI at [http://localhost:8288](http://localhost:8288) (default).

> **Note:** Starting from version **1.10** Visionatrix launches ComfyUI webserver at http://127.0.0.1:8188

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/screenshot_1_dark.jpeg">
    <img alt="Visionatrix UI Light Mode" src="https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/screenshot_1_light.jpeg">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/screenshot_3_dark.jpeg">
    <img alt="Visionatrix UI Light Mode" src="https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/screenshot_3_light.jpeg">
  </picture>
</p>

<details>
  <summary>📹 Click to see a short video demo</summary>

  ![Visionatrix Demo](https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/short_demo.webp)

</details>

## 📥 Installation

### Requirements

- **Python** `3.10` or higher. *(`3.12` recommended)*
- **GPU** with at least `8 GB` of memory *(12GB recommended)*

### Quick Start (Linux/macOS/WSL)

<details>
  <summary>Install prerequisites (Python, Git, etc.)</summary>

  For Ubuntu 22.04:

  ```bash
  sudo apt install wget curl python3-venv python3-pip build-essential git
  ```

  It is also recommended to install FFMpeg dependencies with:

  ```bash
  sudo apt install ffmpeg libsm6 libxext6
  ```
</details>

Download and run the `easy_install.py` script:

> **Note:** This script will clone the Visionatrix repository into your current folder and perform the installation. After installation, you can always run `easy_install` from the "scripts" folder.

Using **wget**:

```bash
wget -O easy_install.py https://raw.githubusercontent.com/Visionatrix/Visionatrix/main/scripts/easy_install.py && python3 easy_install.py
```

Using **curl**:

```bash
curl -o easy_install.py https://raw.githubusercontent.com/Visionatrix/Visionatrix/main/scripts/easy_install.py && python3 easy_install.py
```

Follow the prompts during installation. In most cases, everything should work smoothly.

**To launch Visionatrix** from the activated virtual environment:

```bash
python -m visionatrix run --ui
```

### Quick Start (Windows)

We offer a **portable version** to simplify installation (no need for Git or Visual Studio compilers).

Currently, we provide versions for CUDA/CPU. If there's demand, we can add a DirectML version.

1. **Download**: Visit our [Releases page](https://github.com/Visionatrix/Visionatrix/releases).
2. **Get the Portable Archive**: Download `vix_portable_cuda.7z`.
3. **Unpack and Run**: Extract the archive and run `run_nvidia_gpu.bat` or `run_cpu.bat`.

### Manual Installation

For manual installation steps, please refer to our [detailed documentation](https://visionatrix.github.io/VixFlowsDocs/AdminManual/installation/).

## ⚙️ Post-setup Configuration

### Paths Configurations

The easiest way to set up paths is through the user interface, by going to `Settings->ComfyUI`.

In most cases, the easiest way is to set `ComfyUI base data folder` to some absolute path where you want to store models, task results, and settings.

This will allow you to freely reinstall everything from scratch without losing data or models.

> **Note:** For easy Windows portable upgrades, we assume you have `ComfyUI base data folder` parameter set.

### HuggingFace and CivitAI Tokens

We highly recommend filling in both the
[CivitAI](https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/gated_models/#civitai-api-key) token and the
[HuggingFace](https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/gated_models/#huggingface-token) token in the settings.

Many models cannot be downloaded by public users without a token.

## 🔄 Updating Visionatrix

### For Linux/macOS

Run the `easy_install` script and select the "**Update**" option.

```bash
python3 easy_install.py
```

### For Windows (Portable Version)

Updating the portable version involves:

1. Unpacking the new portable version.
2. Moving `visionatrix.db` from the old version to the new one.

<details>
  <summary>Hint</summary>

  Alternatively, you can specify a custom path for `visionatrix.db` using the `DATABASE_URI` environment variable. This allows you to keep the database file outside the portable archive and **skip step 2**.

  For example, setting DATABASE_URI to:

    `sqlite+aiosqlite:///C:/Users/alex/visionatrix.db`

  will direct Visionatrix to use the `C:\Users\alex\visionatrix.db` file.

</details>

## Docker Compose

Starting with Visionatrix version 2, we provide official Docker images along with a pre-configured `docker-compose.yml` file, making deployment faster and easier. The file is located at the root of the Visionatrix repository.

### Available Services

- **visionatrix_nvidia**: Visionatrix with `NVIDIA GPU` support.
- **visionatrix_amd**: Visionatrix with `AMD GPU` support.
- **visionatrix_cpu**: Visionatrix running on `CPU` only.
- **pgsql**: A PostgreSQL 17 container for the database.

### Usage

- For NVIDIA GPU support:
  ```bash
  docker compose up -d visionatrix_nvidia
  ```

- For AMD GPU support:
  ```bash
  docker compose up -d visionatrix_amd
  ```

- For CPU mode:
  ```bash
  docker compose up -d visionatrix_cpu
  ```

By default, `visionatrix-data` directory will be created in the current directory in the host and used for the `models`, `user`, `input` and `output` files.

You can easily customize the configuration by modifying environment variables or volume mounts in the `docker-compose.yml` file.

## 📚 Documentation and Support

If you have any questions or need assistance, we're here to help! Feel free to [start a discussion](https://github.com/Visionatrix/Visionatrix/discussions/new/choose) or explore our resources:

- **[Documentation](https://visionatrix.github.io/VixFlowsDocs/)**
  - **[Available Flows](https://visionatrix.github.io/VixFlowsDocs/Flows/)**
  - **Admin Manual**
    - [Installation](https://visionatrix.github.io/VixFlowsDocs/AdminManual/Installation/installation/)
    - [Working Modes](https://visionatrix.github.io/VixFlowsDocs/AdminManual/WorkingModes/working_modes/)
    - [Command Line Options](https://visionatrix.github.io/VixFlowsDocs/AdminManual/command_line_options/)
    - [Environment Variables](https://visionatrix.github.io/VixFlowsDocs/AdminManual/environment_variables/)
  - **Flows Developing**
    - [Vix Workflows](https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/vix_workflows/)
    - [Technical Information](https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/technical_information/)
    - [Creating Workflows](https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/comfyui_vix_migration/)
    - [Models Catalog](https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/models_catalog/)
    - [Gated Models](https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/gated_models/)
  - **Common Information**
    - [FAQ](https://visionatrix.github.io/VixFlowsDocs/faq/)
    - [Hardware FAQ](https://visionatrix.github.io/VixFlowsDocs/hardware_faq/)
    - [Hardware Results](https://visionatrix.github.io/VixFlowsDocs/hardware_results/)
    - [OpenAPI](https://visionatrix.github.io/VixFlowsDocs/swagger.html)
