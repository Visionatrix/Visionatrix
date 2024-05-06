.. _SupirUpscaler:

SUPIR Upscaler
==============

*This workflow is added mostly for research purposes, it is still in development.*

**Memory requirements(both VRAM and RAM) are directly related to the input image resolution.**

.. note:: Currently for `macOS runners` `Diffusion type` must be set to `fp32`.

.. note:: Low memory mode: reduces the size of processed tiles to **256**.

.. note:: If you have a very small input image and the result is **less than 1024** (512 for low memory mode) pixels in width **or** height, **tiles should be disabled**.

From `ComfyUI-SUPIR repo <https://github.com/kijai/ComfyUI-SUPIR>`_:

`Memory requirements are directly related to the input image resolution. In my testing I was able to run 512x512 to 1024x1024 with a 10GB 3080 GPU, and other tests on 24GB GPU to up 3072x3072. System RAM requirements are also hefty, don't know numbers but I would guess under 32GB is going to have issues, tested with 64GB.`

Hardware
""""""""

- **Minimum: 12 GB VRAM , 32 GB RAM**
- **Recommended: 16-24 GB VRAM, 64 GB RAM**

*We will not describe the specific time it takes for scaling, because... the flow is still in development and we are constantly trying to improve it.*

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
