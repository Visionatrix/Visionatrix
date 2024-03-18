.. _Stable_Cascade:

Stable Cascade
==============

This flow works much better with text rendering, and supports repeated rendering to generate images in increased resolution with more detail.

Suitable for various fairy-tale or cartoon images or for generating postcards.

One pass image resolution: **1024x576**

Two pass image resolution: **1536x864**

Three pass image resolution: **2048x1152**

Hardware
""""""""

- **Required memory: 8-12 GB**

Time to generate 1 image:

- AMD 7900 XTX: **11.8 sec** / **36 sec** (2 pass)
- NVIDIA RTX 3060 (12 GB): **17 sec** / **49 sec** (2 pass)

Examples
""""""""

.. image:: /FlowsResults/Stable_Cascade_1.png

Prompt: "*portrait of bee, high details, 8k, vivid colors, contrast light*"  (seed: 2)

.. image:: /FlowsResults/Stable_Cascade_2.png

Prompt: "*dolphin at sea, dawn, high details, 8k, vivid colors, contrast light*"  Second Pass: false (seed: 2)

.. image:: /FlowsResults/Stable_Cascade_3.png

Prompt: "*girl with sign 'Cascade', high details, 8k, cinematic*"  (seed: 3)
