.. _Juggernaut_XL:

Juggernaut XL
=============

A fairly simple flow at the moment, simply using the latest **Juggernaut X** model without any post-processing.

.. note:: **Not Safe for Work (NSFW) version.**

Prompting information can be found here: `Juggernaut-X prompting <https://storage.googleapis.com/run-diffusion-public-assets/Prompting_Juggernaut_X.pdf>`_

**Supports various aspect ratios.**

**Supports fast generation using the Align Steps technique**

Hardware
""""""""

- **Required memory: works on 10 GB**

Time to generate 1 image:

- AMD 7900 XTX: **15.8 sec** / **6.7 sec**
- NVIDIA RTX 3060 (12 GB): **35 sec** / **13.5 sec**
- Apple M2 Max: **93 sec** / **39 sec**

Examples
""""""""

.. image:: /FlowsResults/Juggernaut_XL_1.png

Prompt: "*close portrait of hero wearing cuirass sitting on the chair, high details*"  (seed: 2)

.. image:: /FlowsResults/Juggernaut_XL_2.png

Prompt: "*portrait of elf man in obsidian armor looking at viewer from the dark, contrast, high details*"  (seed: 1)

.. image:: /FlowsResults/Juggernaut_XL_3.png

Prompt: "*portrait rage tiger, high resolution*"  (seed: 3)
