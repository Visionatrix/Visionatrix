# Visionatrix

[![Analysis & Coverage](https://github.com/Visionatrix/Visionatrix/actions/workflows/analysis-coverage.yml/badge.svg)](https://github.com/Visionatrix/Visionatrix/actions/workflows/analysis-coverage.yml)
[![Docs](https://github.com/Visionatrix/Visionatrix/actions/workflows/docs.yml/badge.svg)](https://visionatrix.github.io/Visionatrix/)

![PythonVersion](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)


The goal of the project is to provide a user-friendly way for generating and processing images and videos.

To achieve this goal, the [ComfyUI](https://github.com/comfyanonymous/ComfyUI) project was chosen, since its flow format looks very great.

Visionatrix projects provides:

  * *Simplified Setup*:  one-click installation process.
  * *User-Centric Design*:  interface prioritizing ease of use.
  * *Standardized Workflows*:  workflows based on ComfyUI workflow format.
  * *Seamless Integration*:  backend endpoints for task and server management.
  * *Scalability*:  automatic task scheduling across multiple instances.
  * *User Support*:  easily configured to work with multiple users.

> [!NOTE]
> The project is currently in the early development stage, expect breaking changes.

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
2. Download `vix_portable_cuda.7z.001` and `vix_portable_cuda.7z.002`, it is one archive.
3. Unpack it and run `run_nvidia_gpu.bat` or `run_cpu.bat`

### Manual Installation

If you want to perform manual installation, take a look at [documentation](https://visionatrix.github.io/Visionatrix/Installation.html) how to do that.

### User Interface of **Visionatrix**

By default `UI` avalaible at [http://127.0.0.1:8288](http://127.0.0.1:8288)

![UI](/screenshots/screenshot_1.png)
![UI](/screenshots/screenshot_2.png)

## Update process (Linux/macOS)

Run `easy_install` script and select "**Update**" option.

> [!NOTE]
> For portable Windows releases update is a bit tricky:
> 1. Unpack new portable version
> 2. Move `vix_models`, `vix_tasks_files` and `tasks_history.db` to it from the old one
> 3. In most cases where there were no breaking changes it will be enough

## More Information

If you have any questions, we will try to answer them, do not hesitate to create [Discussion](https://github.com/Visionatrix/Visionatrix/discussions/new/choose) and ask.

Some examples of workflow results can be found in **Twitter** by tag [#Visionatrix](https://twitter.com/search?q=%23Visionatrix&src=typed_query)

- [Documentation](https://visionatrix.github.io/Visionatrix/)
  - [Available Flows](https://visionatrix.github.io/Visionatrix/Flows/index.html)
  - [Manual Installation](https://visionatrix.github.io/Visionatrix/Installation.html)
  - [Command Line Options](https://visionatrix.github.io/Visionatrix/CommandLineOptions.html)
  - [Working modes](https://visionatrix.github.io/Visionatrix/WorkingModes.html)
  - [Technical information](https://visionatrix.github.io/Visionatrix/TechnicalInformation.html)
