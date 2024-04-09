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
  * *User Support*: easily configured to work with multiple users.
  * Connecting a custom user backend. _(in plans)_

> [!NOTE]
> The project is currently in the early development stage, expect breaking changes.

## Easy installation for home use

Requirements:

- Python `3.10`*(recommended)* or higher
- Available `git` command (for Windows get it [here](https://gitforwindows.org/))

Download and execute `easy_install.py` script:

> [!NOTE]
> It will clone this repository into the current folder and perform the installation.
> After installation you can always run `easy_install` from the "scripts" folder.

### Linux/macOS/WSL:

With **wget**:
```console
wget -O easy_install.py https://raw.githubusercontent.com/Visionatrix/Visionatrix/main/scripts/easy_install.py && python3 easy_install.py
```

or with **curl**:
```console
curl -o easy_install.py https://raw.githubusercontent.com/Visionatrix/Visionatrix/main/scripts/easy_install.py && python3 easy_install.py
```

### Windows

> [!NOTE]
> If you plan to use `Direct-ML` - **Python3.10** is the only currently supported version by it.
>
> **Requires**: Installed `Microsoft Visual C++ Build Tools` required to build some packages that does not provide binary wheels.

```console
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Visionatrix/Visionatrix/main/scripts/easy_install.py" -OutFile "easy_install.py"; python3 easy_install.py
```

### After that, answer the script's questions and in most cases everything should work.

If you want to perform manual installation, take a look at [documentation](https://visionatrix.github.io/Visionatrix/Installation.html) how to do that.

### Run **Visionatrix**

```console
python -m visionatrix run --ui=client
```

By default `UI` avalaible at [http://127.0.0.1:8288](http://127.0.0.1:8288)

> [!NOTE]
> The default username is ***admin*** with password ***admin***.

![UI](/screenshots/screenshot_1.png)
![UI](/screenshots/screenshot_2.png)

## Update process

Run `easy_install` script and select "**Update**" option.

## More Information

We're in the design process, and as we go,
we'll provide more information in the documentation on how to use it with third-party services or how to add your own media flow.

- [Documentation](https://visionatrix.github.io/Visionatrix/)
  - [Available Flows](https://visionatrix.github.io/Visionatrix/Flows/index.html)
  - [Manual Installation](https://visionatrix.github.io/Visionatrix/Installation.html)
  - [Command Line Options](https://visionatrix.github.io/Visionatrix/CommandLineOptions.html)
  - [Scaling information](https://visionatrix.github.io/Visionatrix/ScalingInformation.html)
  - [Technical information](https://visionatrix.github.io/Visionatrix/TechnicalInformation.html)
