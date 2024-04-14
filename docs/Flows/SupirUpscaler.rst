.. _SupirUpscaler:

SUPIR Upscaler
==============

*This workflow is added mostly for research purposes, it is still in development.*

**Memory requirements are directly related to the input image resolution, so we have added optional downscaling of input.**

.. note:: Currently for `macOS runners` `Diffusion type` must be set to `fp32`.

From `ComfyUI-SUPIR repo <https://github.com/kijai/ComfyUI-SUPIR>`_:

`Memory requirements are directly related to the input image resolution. In my testing I was able to run 512x512 to 1024x1024 with a 10GB 3080 GPU, and other tests on 24GB GPU to up 3072x3072. System RAM requirements are also hefty, don't know numbers but I would guess under 32GB is going to have issues, tested with 64GB.`

From our testing on AMD 7900XTX with `24 GB`:

1. `1024x1024` image - **failed**.
2. `1024x683` image - **success**.
3. `864x864` image - **failed**.
4. `832x832` image - **success**.

Hardware
""""""""

- **Required memory: 10 GB and much more**

Time to upscale 1 image(256x256):

- AMD 7900 XTX: **23 sec** / **24 sec** (2x additional upscale)
- NVIDIA RTX 3060 (12 GB): **x sec** / **x sec** (2x additional upscale)

Time to upscale 1 image(512x512):

- AMD 7900 XTX: **60 sec** / **85 sec** (2x additional upscale)
- NVIDIA RTX 3060 (12 GB): **65 sec** / **116 sec** (2x additional upscale)

Examples
""""""""

*This Upscaler is still in development stage, results may be get better.*

We specifically place one portrait example where results is not perfect.

But for many tests we performed - portrait scaling is shiny compared to older scaling methods.

Image of a classic car:

.. image:: /FlowsResults/SupirUpscaler-classic-car-1024x683.jpg

.. image:: /FlowsResults/SupirUpscaler-classic-car-result.png

Jackie Chan portrait:

.. image:: /FlowsResults/SupirUpscaler-jackie-chan-787x761.jpg

.. image:: /FlowsResults/SupirUpscaler-jackie-chan-result.png

Shakira:

.. image:: /FlowsResults/SupirUpscaler-shakira-711x474.jpeg

.. image:: /FlowsResults/SupirUpscaler-shakira-result.png
