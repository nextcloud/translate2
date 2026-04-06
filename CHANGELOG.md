<!--
  - SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: MIT
-->
# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## 2.3.1 - 2026-04-06

### Changed
- structured changelog in a yaml file ([#86](https://github.com/nextcloud/translate2/pull/86)) @kyteinsky
- add ignore patterns for changelog ([#87](https://github.com/nextcloud/translate2/pull/87)) @kyteinsky

### Fixed
- adjust inference params to limit small input repetition ([#85](https://github.com/nextcloud/translate2/pull/85)) @kyteinsky


## 2.3.0 - 2025-11-21

### Added
- Implement support for taskprocessing trigger event ([#78](https://github.com/nextcloud/translate2/pull/78)) @marcelklehr
- load the model once and keep it loaded ([#82](https://github.com/nextcloud/translate2/pull/82)) @kyteinsky

### Changed
- use "detect_language" instead of "auto" for lang detection enum value ([#75](https://github.com/nextcloud/translate2/pull/75)) @kyteinsky
- update app description in info.xml and readme ([#81](https://github.com/nextcloud/translate2/pull/81)) @kyteinsky

### Fixed
- use cpu device when rocm is the compute device ([#80](https://github.com/nextcloud/translate2/pull/80)) @kyteinsky


## 2.2.0 - 2025-10-06

### Added
- use the config.json from the persistent volume if persent ([#70](https://github.com/nextcloud/translate2/pull/70)) @kyteinsky

### Changed
- set max decoding length to 10k by default ([#69](https://github.com/nextcloud/translate2/pull/69)) @kyteinsky
- bump max NC version to 33

### Fixed
- correct task id from the task object for error reporting ([#69](https://github.com/nextcloud/translate2/pull/69)) @kyteinsky


## 2.1.0 - 2025-08-05

### Added
- Add reuse compliance ([#23](https://github.com/nextcloud/translate2/pull/23)) @AndyScherzinger
- HaRP support (Nextcloud 32+) ([#35](https://github.com/nextcloud/translate2/pull/35)) @oleksandr-nc

### Changed
- pin gh action versions ([#31](https://github.com/nextcloud/translate2/pull/31)) @kyteinsky
- make docker builds reproducible ([#46](https://github.com/nextcloud/translate2/pull/46)) @kyteinsky
- update pip deps and remove dependabot ([#61](https://github.com/nextcloud/translate2/pull/61)) @kyteinsky
- use the HEAD commit timestamp instead of 0 in docker build ([#62](https://github.com/nextcloud/translate2/pull/62)) @kyteinsky
- Improve error handling in task processing ([#65](https://github.com/nextcloud/translate2/pull/65)) @lukasdotcom
- Implement feedback for better error handling ([#66](https://github.com/nextcloud/translate2/pull/66)) @lukasdotcom
- Bump support to NC 32 @kyteinsky

### Fixed
- handle next_task network exceptions @kyteinsky
- fix model switch to work without disable and re-enable ([#32](https://github.com/nextcloud/translate2/pull/32)) @kyteinsky
- report errors to app_api on enable ([#60](https://github.com/nextcloud/translate2/pull/60)) @kyteinsky


## 2.0.3 - 2024-08-23

### Fixed
- handle next_task network exceptions @kyteinsky


## 2.0.2 - 2024-08-23

### Fixed
- graceful shutdown of bg process and fix COMPUTE_DEVICE check @kyteinsky


## 2.0.1 - 2024-08-20

### Fixed
- update pip requirements @kyteinsky


## 2.0.0 - 2024-08-15

### Changed
- drop support for NC29
- moved to the new TaskProcessing API for NC30 @kyteinsky


## 1.1.0 - 2024-08-05

### Added
- feat: madlad model support with ctranslate2 @kyteinsky
- ci: add docker build publish @kyteinsky


## 1.0.0 - 2024-02-23

### Added
- the app @marcelklehr
