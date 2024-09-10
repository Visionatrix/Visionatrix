# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0 - 2024-09-10]

### Added

- New `ComfyUI-BiRefNet` node and **second** Background Removal Flow (**with free license**).
- New **cmd** command: `python3 -m visionatrix orphan-models` to easy clean **models** folder from non-used models. #156
- New UI features: **reset params** button, **touch events** support.

### Changed

- Reworked and finalized the `Inpaint` feature. Now optional `context area` can be passed for the Inpainting. #155

### Fix

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
