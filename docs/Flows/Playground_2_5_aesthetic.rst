.. _Playground_2_5_aesthetic:

Aesthetic images(Playground 2.5)
================================

The flow focuses on three key improvements: enhancing color and contrast, generating images across multiple aspect ratios, and aligning outputs with human aesthetic preferences.


It demonstrates superior performance over previous models and commercial systems in terms of aesthetic quality, especially in generating vibrant colors, accommodating different aspect ratios, and capturing fine details in human-centric images.


Playground v2.5 outperforms widely-used models and even some closed-source systems in user studies focusing on aesthetic preferences.

**Supports various aspect ratios.**

**Supports fast generation using the Align Steps technique**

Hardware
""""""""

- **Required memory: works on 10 GB**

Time to generate 1 image:

- AMD 7900 XTX: **17.5 sec** (no face) / **29 sec** (one face)
- NVIDIA RTX 3060 (12 GB): **33 sec** (no face) / **46 sec** (one face)
- Apple M2 Max: **99.8 sec** (no face) / **160 sec** (one face)

.. note:: Results may vary, as FaceDetailer will post-process image only if it detects face.

Examples
""""""""

.. note:: *On the right is an image with the "fast run" option*

.. image:: /FlowsResults/Playground_2_5_aesthetic_1.png
.. image:: /FlowsResults/Playground_2_5_aesthetic_1-fast.png

Prompt: "*girl in suite looking at viewer, high quality, 8k, bright colors*"  (seed: 5)

.. image:: /FlowsResults/Playground_2_5_aesthetic_2.png
.. image:: /FlowsResults/Playground_2_5_aesthetic_2-fast.png

Prompt: "*cat in suite looking at viewer, high quality, 8k, bright colors*"  (seed: 5)

.. image:: /FlowsResults/Playground_2_5_aesthetic_3.png
.. image:: /FlowsResults/Playground_2_5_aesthetic_3-fast.png

Prompt: "*Dragon in forest, vivid colors*"  (seed: 3)
