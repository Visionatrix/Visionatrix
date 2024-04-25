Manual Installation
===================

In most cases, we recommend using automatic installation via an ``easy-install`` script.

For those who want to install everything manually, here you will find step-by-step instructions on what the script does.

Virtual Environment creation
""""""""""""""""""""""""""""

First clone the repository with :command:`git`::

    git clone https://github.com/Visionatrix/Visionatrix.git && cd Visionatrix


Setup the virtual environment with :command:`python`::

    python -m venv venv


Activate Virtual Environment(**Linux/macOS**) with :command:`source`::

    source venv/bin/activate


Activate Virtual Environment(**Windows**) with :command:`powershell`::

    .\venv\Scripts\Activate.ps1


**PyTorch** installation
""""""""""""""""""""""""

.. note::
    On macOS with Apple Silicon currently no action is needed.

For AMD graphic cards on **Linux** install **ROCM** version of PyTorch using :command:`pip`::

    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0


---------

For AMD graphics cards on **Windows** install PyTorch with DirectML support using :command:`pip`::

    pip install torch-directml


.. note::
    **Python3.10** is the only currently supported version by **torch-directml**.

---------

For NVIDIA graphics cards on **both Linux or Windows** install PyTorch using :command:`pip`::

    pip install torch torchvision torchaudio


Install Visionatrix
"""""""""""""""""""

Install Visionatrix from the previously cloned sources using :command:`pip`::

    pip install .


Run **Visionatrix** initialization command using :command:`python`::

    python -m visionatrix install


Run Visionatrix
"""""""""""""""

Execute from the activated virtual environment **run** command using :command:`python`::

    python -m visionatrix run --ui


Manual Update
"""""""""""""

1. Pull last changes from repository with :command:`git`::

    git pull


2. Execute **update** command from **activated** virtual environment with :command:`python`::

    python -m visionatrix update
