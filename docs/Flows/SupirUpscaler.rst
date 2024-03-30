.. _SupirUpscaler:

SUPIR Upscaler
==============

*This workflow is added mostly for research purposes.*

**Memory requirements are directly related to the input image resolution.**

.. note:: Currently for macOS runners `Diffusion type` must be set to `fp32`.

TO-DO

Reference: `ComfyUI-SUPIR repo <https://github.com/kijai/ComfyUI-SUPIR>`_

Hardware
""""""""

- **Required memory: 10 GB and much more**

Time to upscale 1 image(256x256):

- AMD 7900 XTX: **x sec** / **x sec** (2x additional upscale)
- NVIDIA RTX 3060 (12 GB): **x sec** / **x sec** (2x additional upscale)

Time to upscale 1 image(512x512):

- AMD 7900 XTX: **x sec** / **x sec** (2x additional upscale)
- NVIDIA RTX 3060 (12 GB): **x sec** / **x sec** (2x additional upscale)

Examples
""""""""
