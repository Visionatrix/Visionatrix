.. _Playground_2_5_aesthetic:

Aesthetic images(Playground 2.5)
================================

The flow focuses on three key improvements: enhancing color and contrast, generating images across multiple aspect ratios, and aligning outputs with human aesthetic preferences.


It demonstrates superior performance over previous models and commercial systems in terms of aesthetic quality, especially in generating vibrant colors, accommodating different aspect ratios, and capturing fine details in human-centric images.


Playground v2.5 outperforms widely-used models and even some closed-source systems in user studies focusing on aesthetic preferences.

**Supports various aspect ratios.**

Hardware
""""""""

- **Required memory: works on 10 GB**

Time to generate 1 image:

- AMD 7900 XTX: **17.5 sec** (no face) / **52 sec** (one face)
- NVIDIA RTX 3060 (12 GB): **33 sec** (no face) / **46 sec** (one face)
- Apple M2 Max: **99.8 sec** (no face) / **190 sec** (one face)

.. note:: results may vary, as FaceDetailer will post-process image only if it detects face.

Examples
""""""""

.. image:: /FlowsResults/Playground_2_5_aesthetic_1.png

Prompt: "*girl in suite looking at viewer, high quality, 8k, bright colors*"  (seed: 5)

.. image:: /FlowsResults/Playground_2_5_aesthetic_2.png

Prompt: "*cat in suite looking at viewer, high quality, 8k, bright colors*"  (seed: 5)

.. image:: /FlowsResults/Playground_2_5_aesthetic_3.png

Prompt: "*Dragon in forest, vivid colors*"  (seed: 3)
