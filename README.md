# Visionatrix

[![Analysis & Coverage](https://github.com/Visionatrix/Visionatrix/actions/workflows/analysis-coverage.yml/badge.svg)](https://github.com/Visionatrix/Visionatrix/actions/workflows/analysis-coverage.yml)
[![Docs](https://github.com/Visionatrix/Visionatrix/actions/workflows/docs.yml/badge.svg)](https://visionatrix.github.io/Visionatrix/)

![PythonVersion](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)


The goal of the project is to provide a user-friendly way for generating and processing images and videos.

To achieve this goal, the [ComfyUI](https://github.com/comfyanonymous/ComfyUI) project was chosen, since its flow format looks very great.

**Visionatrix** projects provides:

1. Automatic installation in one click.
2. Extended format of ComfyUI workflows.
3. Constant task history.
4. Backend endpoints for tasks & server management.
5. User interface which is much simpler and user-oriented
6. Support for multiple users. _(in progress)_
7. Connecting a custom user backend. _(in progress)_
8. Support of queue manager to schedule tasks between multiply instances. _(in progress)_

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

```console
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Visionatrix/Visionatrix/main/scripts/easy_install.py" -OutFile "easy_install.py"; python3 easy_install.py
```

### After that, answer the script's questions and in most cases everything should work.

If you want to perform manual installation, take a look at [documentation](https://visionatrix.github.io/Visionatrix/Installation/index.html) how to do that.

### Run **Visionatrix**

```console
python -m visionatrix run --ui=client
```

By default `UI` avalaible at [http://127.0.0.1:8288](http://127.0.0.1:8288)

![UI](/screenshots/screenshot_1.png)
![UI](/screenshots/screenshot_2.png)

## Update process

Run `easy_install` script and select "**Update**" option.

## More Information

We're in the design process, and as we go,
we'll provide more information in the documentation on how to use it with third-party services or how to add your own media flow.

- [Documentation](https://visionatrix.github.io/Visionatrix/)
  - [Available Flows](https://visionatrix.github.io/Visionatrix/Flows/index.html)
  - [Manual Installation](https://visionatrix.github.io/Visionatrix/Installation/index.html)
