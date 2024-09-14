# Visionatrix

[![Analysis & Coverage](https://github.com/Visionatrix/Visionatrix/actions/workflows/analysis-coverage.yml/badge.svg)](https://github.com/Visionatrix/Visionatrix/actions/workflows/analysis-coverage.yml)
[![Docs](https://github.com/Visionatrix/VixFlowsDocs/actions/workflows/docs.yml/badge.svg)](https://visionatrix.github.io/VixFlowsDocs/)
[![Models Catalog](https://github.com/Visionatrix/VixFlowsDocs/actions/workflows/check-models-catalog.yml/badge.svg)](https://github.com/Visionatrix/VixFlowsDocs/actions/workflows/check-models-catalog.yml)

![PythonVersion](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)

<div align="center">
 <img alt="Visionatrix" height="200px" src="https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/logo.png">
</div>

The goal of the project is to provide use of [ComfyUI](https://github.com/comfyanonymous/ComfyUI) workflows in an easy way.

Visionatrix features:

  * **Simplified Setup and Update**:  a simple installation and update process to new versions.
  * **Minimalistic UI**:  designed for daily use of workflows.
  * **Stable Workflows**:  versioning and update processes for workflows to new versions.
  * **Scalability**:  support for multiple instances with multiple task workers running simultaneously.
  * **Multiple User Support**:  easily configured to work with multiple users and integrate different user backends.
  * **LLM power**:  easy integration with Ollama/Gemini for use as LLM for ComfyUI Workflows.
  * **Seamless Integration**:  operates as a service with backend endpoints and webhook support.

> [!NOTE]
> Since we are already approaching the release of version 1.0 and all the decisions for how the project will look are completed -
> we are welcome to the new ideas which we can implement further.
>
> If you wish to join the development, feel free to do so.

### User Interface of **Visionatrix**

By default `UI` avalaible at [http://127.0.0.1:8288](http://127.0.0.1:8288)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/screenshot_1_dark.jpeg">
  <img alt="Visionatrix UI" src="https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/screenshot_1_light.jpeg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/screenshot_3_dark.jpeg">
  <img alt="Visionatrix UI" src="https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/screenshot_3_light.jpeg">
</picture>

<details>

  Short [video demo](https://github.com/Visionatrix/VixFlowsDocs/blob/main/screenshots/short_demo.webp)

  ![Visionatrix Demo](https://raw.githubusercontent.com/Visionatrix/VixFlowsDocs/main/screenshots/short_demo.webp)

</details>

## Easy installation for home use

Requirements:

- Python `3.10`*(recommended)* or higher
- GPU with at least minimum `10 GB` of memory *(12GB is recommended)*

### Linux/macOS/WSL:

Download and execute `easy_install.py` script:

> [!NOTE]
> It will clone this repository into the current folder and perform the installation.
> After installation you can always run `easy_install` from the "scripts" folder.

With **wget**:
```console
wget -O easy_install.py https://raw.githubusercontent.com/Visionatrix/Visionatrix/main/scripts/easy_install.py && python3 easy_install.py
```

or with **curl**:
```console
curl -o easy_install.py https://raw.githubusercontent.com/Visionatrix/Visionatrix/main/scripts/easy_install.py && python3 easy_install.py
```

After that, answer the script's questions and in most cases everything should work.

Command to launch Visionatrix from an activated virtual environment::

```console
python -m visionatrix run --ui
```

### Windows

We provide a **portable version** in the form of an archive.
This eliminates the need to have `Git` and `Visual Studio` compilers installed.
Currently, only versions for CUDA/CPU is build, if there will be request we can add `Direct-ML` version too.

1. Go to [Releases](https://github.com/Visionatrix/Visionatrix/releases)
2. Download `vix_portable_cuda.7z.001` *(and `vix_portable_cuda.7z.002`, if present, then this is one archive)*.
3. Unpack it and run `run_nvidia_gpu.bat` or `run_cpu.bat`

### Manual Installation

If you want to perform manual installation, take a look at [documentation](https://visionatrix.github.io/VixFlowsDocs/Installation.html) how to do that.

## Update process (Linux/macOS)

Run `easy_install` script and select "**Update**" option.

> [!NOTE]
> For portable Windows releases update is a bit tricky:
> 1. Unpack new portable version
> 2. Move `vix_models`, `vix_tasks_files` and `tasks_history.db` to it from the old one
> 3. In most cases where there were no breaking changes it will be enough

## More Information

If you have any questions, we will try to answer them, do not hesitate to create [Discussion](https://github.com/Visionatrix/Visionatrix/discussions/new/choose) and ask.

- [Documentation](https://visionatrix.github.io/VixFlowsDocs/)
  - [Available Flows](https://visionatrix.github.io/VixFlowsDocs/Flows/index.html)
  - [Manual Installation](https://visionatrix.github.io/VixFlowsDocs/installation/)
  - [Command Line Options](https://visionatrix.github.io/VixFlowsDocs/command_line_options/)
  - [Working modes](https://visionatrix.github.io/VixFlowsDocs/working_modes/)
  - [Vix Workflows](https://visionatrix.github.io/VixFlowsDocs/vix_workflows/)
  - [Creating Workflows](https://visionatrix.github.io/VixFlowsDocs/comfyui_vix_migration/)
  - [Technical information](https://visionatrix.github.io/VixFlowsDocs/technical_information/)
  - [FAQ](https://visionatrix.github.io/VixFlowsDocs/faq/)
  - [Hardware FAQ](https://visionatrix.github.io/VixFlowsDocs/hardware_faq/)
  - [Hardware Results](https://visionatrix.github.io/VixFlowsDocs/hardware_results/)
  - [OpenAPI](https://visionatrix.github.io/VixFlowsDocs/swagger.html)
