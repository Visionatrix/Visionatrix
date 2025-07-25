# Changelog

All notable changes to this project will be documented in this file.

## [2.7.0 - 2025-07-25]

### Added

- Ability to remove `workers` from the UI(mostly needed for docker installs). #460
- Support of `LDAP` as a user backend. #454
- Ability to disable `User Settings`. #466

### Changed

- ComfyUI and Comfy-Manager updated to the latest versions. #469

## [2.6.0 - 2025-07-01]

### Added

- New flows: `Flux Kontext` and `Restore Old Photo`.
- Docker Compose: ability to specify CUDA version. #441 Thanks to @julienym
- Pre-init ComfyUI engine settings from the database. #436
- New **sync** endpoint to create task and receive a result(*for the upcoming MCP*). ##442
- Added `gemma-3-12b-it` and `gemma-3-27b-it` models. #448

### Changed

- Flow `SDXL Ghibli` was replaced with flow `Ghibli (Flux Kontext)`.
- Replaced `gemini-1.5-flash-002` and `gemini-1.5-pro-002` with `gemini-2.5-flash` and `gemini-2.5-pro`. #435

### Fixed

- UI: "Reset params button" - detection of default value of the `Aspect Ratio` parameter. #437
- UI: correct displaying results of hidden tasks(like `Ask AI`). #445
- Correctly rewire existing optional input param when disconnecting optional input node form graph. #443
- Update process: restart the process after installing the new basic python packages for ComfyUI. #444
- Docker image for AMD: do not run multiple workers to prevent running worker on APU.
- Adding `LoRAs` to the flows in new clean installations. #447
- Update process between the release versions. #452

## [2.5.1 - 2025-06-06]

### Added

- Docker(CUDA): from now Visionatrix will use all available GPUs by default. #427

### Fixed

- Windows: fix broken `filterpy` package which leads to errors in many flows. #426
- SettingsUI(Workers): correctly display `Smart Memory`, `VRAM State`,.. details. #429
- SettingsUI(Comfy): `Show ComfyUI folders` button now works even when you did not set custom path to models. #430
- NPM packages update. #424
- Security issue. Big thanks to @protozeit for reporting it.

## [2.5.0 - 2025-05-30]

### Added

- Option to set `reserve-vram` parameter for Workers from UI. #421
- Ability to override `smart-memory`, `vae_cpu`, `reserve-vram`, `cache-type` for specific workers from UI. #420

### Changed

- Default model for LLM and VLM now is `gemma3:12b-it-qat` instead of `qwen2.5:14b`. #414
- `ComfyUI_FizzNodes` node pack was dropped from the basic node list, as abandoned. #415

### Fixed

- Federation and Global Worker Settings are hidden from non-admin users. #411
- Gemini node is now used with GOOGLE_API_KEY environment variable and did not get saved in the workflow. #418
- ComfyUI required packages now prioritized by ComfyUI-Manager to not break ComfyUI`s dependencies. #417

## [2.4.1 - 2025-05-18]

### Added

- UI option to enable processing `VAE` on the CPU, located in the **Settings -> Workers** page. #408

### Changed

- `Smart Memory` is enabled by default (like it was before `2.4.0` version). #407

## [2.4.0 - 2025-05-17]

### Added

- New **ACE-Step Audio music flow**.
- Enabling/disabling ComfyUI `Smart Memory` now should be done from the **Settings -> Workers** UI page. **By default** `Smart memory` will be disabled. #403
- Changing ComfyUI **cache** settings(`lru`, `none`) now should be done from the **Settings -> Workers** UI page. #404
- Enabling/disabling ComfyUI `save metadata` option now should be done from the **Settings -> Settings** UI page. **By default** `save metadata` will be disabled. #402

### Changed

- CUDA: For the new installations will be used `12.8` version to support NVIDIA `5xxx` series graphic cards.
- `rgthree-comfy` node was removed from the basic node list. #405

## [2.3.0 - 2025-05-07]

### Added

- Automatic update of Flows when version changes(mostly for Docker installs).
- Support for `QuadrupleCLIPLoader` node, HiDream flow. #396
- Ability for integrations to easily exclude nodes and flows. #395 #394
- Mirroring od docker images to `docker.io`. #388

### Changed

- Removed WAS-node-suite from the default nodes list. #383
- Updated ComfyUI to **v0.3.31** and Nodes to the latest versions. #385 #394
- Refactored code to be fully async, even in `__main__.py`. #386

### Fixed

- Lowered size of Windows Standalone Package. #384

## [2.2.0 - 2025-04-21]

### Added

- New Photomaker flow based on the new `InfiniteYou` tech from ByteDance. #359
- The new `gemini-2.0-flash-lite-001` model can now be configured to use LLM. #365
- New `background tasks` engine; refactored `federation feature` to use it. #367

### Fixed

- UI: Much less spam with warnings when Ollama is not found. #364
- UI: Updated packages to last versions. #373
- Much more advanced parallel model loading/flows install algorithm. #362
- Deselecting LoRA from the existing flow now correctly allows to save the modified flow. #361
- Adjusted memory requirements to mark flows as supported; UI correctly displays advanced options when `is_seed_supported=False`. #381
- The log level is now set correctly when Visionatrix is started directly from `uvicorn`. #366
- Now when running Visionatrix directly from `uvicorn` the correct values settings are read from the database. #369

## [2.1.0 - 2025-03-30]

### Added

- `3D` flows support, `Hunuyan 3D` flow. #356
- Initial support(beta) for `Federation`. Connection of the remote Visionatrix-es to your local one. #357

### Changed

- `Visionatrix` tasks results now stored in the `visionatrix` subfolder of `output` folder. #349
- `Input` files for tasks are now stored with extensions. #351

### Fixed

- Optimized Dockerfile, fixed not working docker images deploying for `Novita.ai`. #354
- macOS: `ComfyUI-Frame-Interpolation` node(for `AllYourLife` flow) now works correctly. #352
- Invalid model download path for `ComfyUI-Frame-Interpolation` node models, that were leading to duplicates. #357

## [2.0.0 - 2025-03-15]

If you have any problems with this version, feel free to ask questions [here](https://github.com/Visionatrix/Visionatrix/issues/332).

### Added

- `Animagine XL v4` and `RealVis v5` basic SDXL flows.
- New `HunyuanVideo` flow; updated `LTXV` video flow.
- `Surprise Me` - new feature to use LLM to create a random prompt. #314
- `RemoteVAE` feature for systems with low-vram. #345
- UI: filter to show **only installed flows**. #316
- UI: **Export flow** button. #321
- UI: now supports **editing** Flow metadata. #323
- UI: display current version of Visionatrix. #325
- UI: `send to flow` now support custom parameters. #344
- Docker images, docker compose. #339

### Changed

- **Main achievement**: Folder with models now always should be defined and works correctly for the most custom nodes. **Reinstalling of some Flows required if it breaks them.**
- `ComfyUI-Manager` is now used to install custom nodes.. #331

### Fixed

- **Easy installation script** now performs early check for the compilers to be present(*Linux only*). #319
- Support for `ComfyUI Manager`. #318
- Prompt translations feature now works correctly with **Ollama** thinking models. #320
- Endpoint to **uninstall** flow now correctly immediately updates the installed flow cache. #327
- Fixed broken flows **Mad Scientist** and **PhotoStickers 2**.

## [1.11.1 - 2025-02-22]

### Changed

- **Major** internal refactoring of the backend was carried out, and the logic in **Default** and **Server** modes was unified. #309

### Fixed

- `Server mode`: Now works correctly on fresh installations with no flows installed.
- `Server mode`: Prompt translations using **Gemini** now works correctly.
- `Worker to Server` mode now works correctly.

## [1.11.0 - 2025-02-16]

Nodes `style_aligned_comfy` and `comfyui-art-venture` were removed. Feel free to remove them manually in old installations.

### Added

- Dynamic `LoRAs` support. For most basic Flows you can now easy add new loras from the `CivitAI`! #303
- Added support for `OllamaConnectivityV2` node.
- New `gemini-2.0-flash-001` model available for selection in settings. #305
- Support for tasks with output text files as a results(node `SaveText|pysssss`). #304

### Changed

- Settings UI: For `Ollama` now dropdown list with available models displayed. #300

## [1.10.0 - 2025-01-19]

If you use `extra_model_path.yaml` for configuring path to models, please add `birefnet` entry to it.

### Added

- `ComfyUI` can now be opened from the Visionatrix UI (**alpha**, not all features are functional). #279
- New flows: `LTXV-video`, `Pencil Sketch Portrait`, `Animal Clothing`, `SD3.5-Large`, `SD3.5-Medium`, `PixArt E`, `Aura Flow`.
- UI: Added a filter for `supported` flows and memory requirements for each flow. #285
- UI: Orphan models are now accessible in `Settings -> ComfyUI`. #274
- UI: Displays required size for each model and for all models in a flow. #275
- New `ComfyUI_BiRefNet_ll` node. #281
- New `ComfyUI_PuLID_Flux_ll` node. #289
- The `SaveAnimatedWEBP` output node is now supported. #276

### Changed

- All `Remove background` flows now use the new `ComfyUI_BiRefNet_ll` node, which supports path mappings.

### Fixed

- Improved description of steps to take if the `extra_model_paths.yaml` file is missing entries.
- UI: Reduced spam requests to the backend when installing multiple flows in parallel. #280
- The `--cache_lru` ComfyUI command-line argument is now correctly supported. #286
- Resolved an issue where flows using `Ollama` occasionally broke due to Visionatrix generating an unsupported random seed value for the Ollama node.

## [1.9.0 - 2024-12-17]

Please rename **tasks_history.db** to **visionatrix.db** before or after the update.

### Added

- New built-in node added: **ComfyUI-KJNodes**. #257
- New built-in node added: **ComfyUI_LayerStyle**. #259
- New built-in node added: **ComfyUI-Easy-Use**. #270
- New `Flux Extend` and `Pencil Sketch` flows.
- Support for the CivitAI API key. #258
- `easy_install` script: ability to create `extra_model_paths.yaml` later, after installation. #262
- Flows Developing: [GUI](https://visionatrix.github.io/VixFlowsDocs/FlowsDeveloping/models_catalog/) to easily add models to the **model catalog**.

### Changed

- Changed the default **SQLite** database name to **visionatrix.db** as we start storing much more data in the database.
- Improved parallel installation of flows, model downloads, and more robust integration with the part of ComfyUI responsible for these tasks.

### Fixes

- `Database is locked` error for **SQLite** database. #269
- Correct handling of **ctrl+c** for the "install-flow" terminal command.
- Pinned to the latest version of ComfyUI, which fixes the `Photomaker` flow and some other issues.
- Added correct path mappings to `ultralytics_bbox` and `ultralytics_segm` models folders. #273
- Added correct path mappings to `sams` models folder with fix in `comfyui-art-venture` node. #272
- UI: `Worker` with invalid status `offline` when it should be `online`.
- UI: Updated Node.js packages. #265

## [1.8.0 - 2024-11-29]

This release introduces some breaking changes that are incompatible with previous versions.
Feel free to create issues or discussions if anything is unclear. We are working towards providing a much smoother experience starting with the `2.0` series.

### Added

- Support for the `--extra-model-paths-config` ComfyUI argument. #240
- The `MODELS_CATALOG_URL` option now supports multiple addresses. #251
- Model catalogs now use the same versioning scheme as `FLOWS_URL`, which will help prevent a situation where a format change for new versions causes all old ones to stop working. #252
- **Parallel** installation of (work)flows is now supported. #244

### Changed

- The `--flows_dir` argument and `FLOWS_DIR` environment variable have been removed. This information is now stored in the database. #242
- The `vix_backend` folder has been renamed to `ComfyUI`. Please rename it manually if you are updating from a previous version, or perform a clean installation. #250
- The default CUDA version for new installations has been updated from `12.1` to `12.4`. #239

### Fixed

- Resolved cases where the `buffalo_l.zip` installation (InsightFace) led to duplicate models in the filesystem. #249

## [1.7.0 - 2024-11-23]

Emergency release due to update of `yolo`(Impact-Node) HuggingFace models, which broke our all new installations for all versions.

### Added

- UI: button to show task result's input files. #233

### Changed

- **Removed** `--models_dir` argument to rely solely on ComfyUI algorithm and support multiple directories for models. #236
- **Backend API Breaking change**: API URL has been moved from `/api` to `/vapi`. #237
- **Reworked** `--openapi` command to support more functionality and be easier to use. #231

### Fixed

- OpenAPI specs: now correctly fills the default values with `float`, `bool`, `int` input types for flows. #234

## [1.6.0 - 2024-11-14]

This release focuses on simplifying the process of writing integrations and fixing bugs found in version `1.5`.

### Added

- The `install-cmd` command now accepts directories, allowing installation of all flows from a specified directory. #206

### Changed

- Windows archive release size greatly reduced(minus 2GB) and now fits into **1** archive file. #225
- The default `pytorch` version for new installations has been updated to `2.5.1`.
- The old, deprecated endpoint for task creation has been removed. #209
- The deprecated `--loglevel` command-line argument has been removed. #218

### Fixed

- **UI**: Images were not displayed during the `Send to flow` action. #205
- **UI**: Tasks are now sorted by the `finished_at` column. #211
- **UI**: Corrected settings descriptions, added links to docs. #224
- **UI**: Error creating flow after updating flow if parameter names changed. #229
- The `seed` parameter was ignored in the new `task creation` endpoint. #210
- **macOS**: The `PYTORCH_ENABLE_MPS_FALLBACK` setting is now correctly applied, and flows like `SUPIR`, `remove background`, etc., work again. #212
- The `Gemini model` setting is now respected by the backend. #214 #217
- The `Ollama keepalive` setting is now respected by the backend. #215
- The `seed` parameter is now correctly included in the new `OpenAPI specs` for Flows. #216
- Disabled automatic update checks for the "Albumentations" package. #221
- The translations feature can now be used for non-`VixUI*` classes. #220

## [1.5.0 - 2024-10-31]

### Added

- Vide Flows: Support of flows with video as result. #192
- First video flow: [AllYourLife](https://visionatrix.github.io/VixFlowsDocs/Flows/AllYourLife/)
- Additional new flows: **Proteus** and **SD3.5**.

### Changed

- Now by default `localhost` is used instead of `127.0.0.1`
- `--loglevel` cmd argument is deprecated, and the same argument(`--verbose`) as in ComfyUI takes it place. #201
- `ComfyUI_Gemini_Flash` node was [replaced](https://github.com/Visionatrix/Visionatrix/commit/ce52839ee42cca6ae5cad08cc13771440930efbd) with `ComfyUI-Gemini` node with additional support for **Gemini Pro** model.
- Devs: new endpoint for creating tasks. Much easier implementing integrations, Gradio examples for ComfyUI flows will come in `1.6` version.

### Fixed

- UI now fetches all settings from backend in a single request. #200
- `install-flow` cmd command now can accept `tags` and you can use patterns with it. #198
- **Install ALL(4)** option in `easy_install.py` script now correctly installs **all** flows using `*` pattern. #198
- Parse of models from `CLIPLoader` and `TripleCLIPLoader` basic ComfyUI nodes. [commit](https://github.com/Visionatrix/Visionatrix/commit/63f6cbc351d98b5926e8f0d4d1f9ea1b0c07f95e)

## [1.4.1 - 2024-10-11]

### Fixed

- UI can now display the original of translated generation prompt without reloading the page. #195
- Installing the `ultralytics` package for ComfyUI-Impact-Pack. #194

## [1.4.0 - 2024-10-08]

### Added

- **Translations for Prompts** with help of Ollama or Gemini. #178
- `PhotomakerPlus` node and `Photomaker 2` flow. #184
- UI: priority toggle for tasks in queue. #188
- Always resume download of an incomplete model, if possible. #175
- Backend: endpoint to fetch all settings at one. #180
- Ability to specify multiple values in `options.FLOWS_URL`. #187

### Fixed

- ImpactNode: separately download required models during Workflow installation. #181
- Worker asks for User settings before Global. #182

## [1.3.0 - 2024-09-24]

Release with bug fixes and minor features found after testing in production environment.

### Added

- New `MAX_PARALLEL_DOWNLOADS` environment option(default=`2`) for parallel models downloading. #159
- New `NODES_TIMING` environment option to print execution time of each node(for debug). #172
- Tasks' `priority` feature(backend part only). #173

### Fixed

- Fixed GPU memory being freed at certain times (for rare cases). Enable memory freeing on AMD GPUs. [#74bb44d](https://github.com/Visionatrix/Visionatrix/commit/74bb44d69e9e2829673118cc8eadb958e684e194)
- Perform several attempts to clone repos, before failing. #162
- Ignore ComfyUI `execution_cached` event without nodes cached(fixes rare negative progress value). #163
- Stop duplicating logs twice. #164
- NodeJS packages update. #169

## [1.2.0 - 2024-09-10]

### Added

- New `ComfyUI-BiRefNet` node and **second** Background Removal Flow (**with free license**).
- New **cmd** command: `python3 -m visionatrix orphan-models` to easy clean **models** folder from non-used models. #156
- New UI features: **reset params** button, **touch events** support.

### Changed

- Reworked and finalized the `Inpaint` feature. Now optional `context area` can be passed for the Inpainting. #155

### Fixed

- Different UI fixes and adjustments. #155

## [1.1.0 - 2024-09-01]

### Added

- Basic `Inpaint` support. New Flux + ColorfulXL redraw workflows. #151
- New `--reserve-vram` and `--fast` commandline options from the last ComfyUI. #148

### Fixed

- Now for nodes like `ComfyUI_InstantID` or `ComfyUI-BRIA_AI-RMBG`, their required models are displayed in the flow models. #149

### Changed

- ComfyUI updated with PR #2666 (Execution Model Inversion)

## [1.0.1 - 2024-08-20]

### Fixed

- Unable to stop flow installation in Server mode.
- Spam with authentication errors in Server mode. (incorrect `bcrypt` version was pinned)
- Webhooks were not working in some special cases.

## [1.0.0 - 2024-08-17]

### Added

- **Child tasks: Send the result of a task to other tasks and work with it further on the same page.** #124
- Support for `HEIF`/`HEIC` files as input. #135
- Workflows with `Flux`: 16 and 8 bits and 'realism' lora.
- Workflow with `HunyuanDiT` model.

### Changed

- Replaced `ComfyUI-AutomaticCFG` with `Skimmed_CFG` node. #126
- `ColorfulXL` workflow was updated to use the last version of model.
- **Breaking API Change**: `/api/tasks/create` endpoint was changed from `POST` to `PUT` method. #139

### Fixed

- Fixed `Update flow` action in backend(UI was affected). #128
- Support for workflows without explicit models. #134
- Better support of different ComfyUI nodes. #125 #138
- Many other UI bug fixes.

## [0.9.0 - 2024-07-28]

### Added

- `OLLAMA_VISION_MODEL` setting/env var to override vision model that used in workflows. #116
- `ComfyUI_Gemini_Flash` node with free `Flash` model and proxy support for that. #118
- `/flow-update` endpoint and ability to see in UI which workflows have updates. #120

### Changed

- `Photo Stickers2` and `Mad Scientist` workflows can optionally use `Google Gemini` instead of **Ollama**.

## [0.8.0 - 2024-07-15]

To use `PuLID_ComfyUI` you need manually add to `extra_model_paths.yaml` file the `pulid: /!YOUR_PATH!/Visionatrix/vix_models/pulid` line OR to run `easy_install.py` and run "reinstall backend".

### Added

- New `Photo Stickers2` workflow! Author: **Datou**.
- Initial support for webhooks for easier integration into services.
- `PuLID_ComfyUI`, `ComfyUI_FizzNodes` and `style_aligned_comfy` nodes to the default nodes list.

### Changed

- `ColorfulXL` model/flow was updated to use the last version(**7.0**) of model.

## [0.7.1 - 2024-07-07]

### Added

- [OpenAPI documentation](https://visionatrix.github.io/VixFlowsDocs/swagger.html) #106 #107

### Changed

- Most **Backend endpoints** were renamed to be better understandable. #108

### Fixed

- Version `0.7.0` was broken in `SERVER` + `WORKER` mode, due to a bug with invalid urls.

## [0.7.0 - 2024-07-05]

### Added

- New `Mad Scientist` workflow. Author: **Datou**.
- Added `comfyui-ollama` and `ComfyUI-AutoCropFaces` nodes. #105
- Added support for auto downloading models for `IP-Adapter` presets(`IPAdapterUnifiedLoader` node). #105
- `POST` method for `/flow` endpoint to install flow with uploading workflow file(it is the same as `install-flow` command line option) #102

### Changed

- The installation status of flows has been moved from the dictionary to the database(to full support instances with multiple Web workers). #101

## [0.6.0 - 2024-06-29]

**Note: Update `can be` broken from the previous versions, as `git` repository was [cleaned up](https://github.com/Visionatrix/Visionatrix/issues/100)**

### Added

- The set of nodes `was-node-suite-comfyui` and `comfyui-art-venture` have been added to the default set of Nodes.

### Changed

- **Full rework of Workflow concept**: now Visionatrix workflows does not require additional files and is the same as ComfyUI workflows. #96

### Fixed

- Miscellaneous UI fixes and enhancements.

## [0.5.0 - 2024-06-21]

### Added

- Implemented version control of `workflows`, now adding new workflows should not break old versions of Vix. #88
- Added prompt attention editing on `CTRL + ArrowUp/ArrowDown` like in ComfyUI. #90
- Implemented ability to change of the worker option `tasks_to_give` in the Settings. #93

### Changed

- All backend endpoints are prefixed with `/api` from now. #91

## [0.4.0 - 2024-06-15]

**Breaking change: new database needs to be created, just delete the old one. This is the last time.**

### Added

- **Settings** and **Workers** UI pages, support for `gated` models, `SD3` flow. #85
- `alembic` to perform database migrations and not to recreate Database in the future. #83

### Fixed

- Removed relation between `users` table and others, which now correctly allows to implement connection of third party user backends.
- In some cases, when commits were reverted in the node's remote repositories, the `update` command completed with an error. #87
- Other small bugfixes for UI and backend part.

## [0.3.0 - 2024-06-09]

### Added

- New simple workflows `Colorful XL` and `Mobius XL`.

### Changed

- Documentation and `Flows`/`Models` data was moved to a separate repo: https://github.com/Visionatrix/VixFlowsDocs

### Fixed

- `easy_install.py` script `update` and `install` commands now has correct algo for the **release** and **dev** versions. #79

## [0.2.0 - 2024-05-27]

Breaking change: new database needs to be created(new fields was added), just delete the old one.

### Added

- New Memoji workflow. #76
- Ability/example how to use Nextcloud instance as a user backend. #70
- `VIX_SERVER_WORKERS` env variable for `SERVER` mode to spawn multiple server instances. #72
- `LOG_LEVEL` env variable to set Log level. #72
- `worker_version`, `tasks_to_give` fields to the `workers` table.

### Fixed

- Support for `uvicorn visionatrix:APP` command. #72
- Miscellaneous fixes and enhancements.

## [0.1.0 - 2024-05-13]

Breaking change: new database needs to be created(new fields was added), just delete the old one.

### Added

- Option `Fast(AlignYourSteps)` for `Aesthetic(Playground)` and `Juggernaut` workflows.
- `locked_at`, `created_at`, `updated_at`, `finished_at` - new fields in the task details.
- `/workers_info` endpoint to get information about Workers instead of `/system_stats`.

### Changed

- **SUPIR Upscaler workflow rework**: tiles support(to process large images), optional "soft" mode without sharpening.
- `/task-restart` endpoint: added `force` optional parameter, which allows to restart the task which has no "error" state set.

### Fixed

- Miscellaneous fixes and enhancements.

## [0.0.9 - 2024-04-28]

Breaking change: please remove old `juggernaut_lighting_loras` folder from *vix_flows* folders.

### Added

- `Send to` button - in one click, send the result of one workflow for processing to another.
- Optimization: priority of execution of task of the same type as the last one, if possible.
- `ComicU` flow: added option to make clear Anime style portraits.
- `Juggernaut XL` flow: easy use of the latest **Juggernaut X** model.
- From now on, each repository will be tagged each release, allowing you to install a specific version of **Vix**.

### Changed

- AMD graphic cards: `Nightly PyTorch 2.3` replaced with `stable` version.
- `Juggernaut Lighting Loras` renamed to `Juggernaut Lite` flow.

### Fixed

- Added cache for installed Workflows list to not read it from disk everytime.

## [0.0.8 - 2024-04-20]

### Added

- Windows Portable `CUDA`/`CPU` version.

### Fixes

- Various bugs were fixed in the distributed Server-Worker mode.

## [0.0.7 - 2024-04-14]

### Added

- Initial support for multiple users.
- New `execution_time` field in Tasks.
- `Aspect Ratio` option in `Playground 2.5` and `Juggernaut Lighting` flows.
- Optional parameter for downscaling of input image to SUPIR workflow.

### Fixes

- Many fixes to `Server` and `Worker` modes.

## [0.0.6 - 2024-04-08]

### Added

- **Docker** container as an alternative way for easy run.
- **Scaling**: ability to run instances of **Vix** in additional `Server` or `Worker` modes.
- `Restart` button in UI for tasks with `Error` status set.

### Fixed

- ``--cpu`` flag is automatically applied if AMD or NVIDIA PyTorch is not found.

## [0.0.5 - 2024-03-30]

### Added

- `SUPIR` upscaler workflow.
- Semi-automatic process of models detection on ComfyUI workflows.

### Fixed

- Slightly better progress detection for cached workflows.

## [0.0.4 - 2024-03-26]

### Added

- Now tasks engine uses SqlAlchemy with default SQLite instead of `json` file.
- Initial support of processing tasks queue in parallel.
- `ComicU Portrait` workflow.

### Fixed

- Small UI adjustments.

## [0.0.3 - 2024-03-23]

### Added

- Support for **ComfyUI** command line arguments.
- Simplified implementation of **ComfyUI** workflows: added automatic mapping of output data instead of manual one.

### Changed

- Tasks engine rework: `ComfyUI` was incorporated in `Vix`, now all runs in one process.

## [0.0.2 - 2024-03-20]

### Changed

- Persistent task history, polished UI, `6` working and useful workflows.

## [0.0.1 - 2024-03-12]

### Added

- First release, although there is a lot missing the concept - is working.
