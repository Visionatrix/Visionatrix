# Changelog

All notable changes to this project will be documented in this file.

## [0.0.4 - 2024-04-26]

## Added

- Now tasks engine uses SqlAlchemy with default SQLite instead of `json` file.
- Initial support of processing tasks queue in parallel.
- `ComicU Portrait` workflow.

## Fixed

- Small UI adjustments.

## [0.0.3 - 2024-04-23]

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
