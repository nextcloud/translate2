<!--
  - SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: MIT
-->
# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## 2.1.0 – 2025-08-05
### Added
- Add reuse compliance (#23) @AndyScherzinger
- HaRP support (Nextcloud 32+) (#35) @oleksandr-nc

### Fixed
- handle next_task network exceptions @kyteinsky
- fix model switch to work without disable and re-enable (#32) @kyteinsky
- report errors to app_api on enable (#60) @kyteinsky

### Changed
- pin gh action versions (#31) @kyteinsky
- make docker builds reproducible (#46) @kyteinsky
- update pip deps and remove dependabot (#61) @kyteinsky
- use the HEAD commit timestamp instead of 0 in docker build (#62) @kyteinsky
- Improve error handling in task processing (#65) @lukasdotcom
- Implement feedback for better error handling (#66) @lukasdotcom
- Bump support to NC 32 @kyteinsky


## 2.0.3 – 2024-08-23
### Fixed
- handle next_task network exceptions @kyteinsky

## 2.0.2 – 2024-08-23
### Fixed
- graceful shutdown of bg process and fix COMPUTE_DEVICE check @kyteinsky

## 2.0.1 – 2024-08-20
### Fixed
- update pip requirements @kyteinsky

## 2.0.0 – 2024-08-15
### Changed
- drop support for NC29
- moved to the new TaskProcessing API for NC30 @kyteinsky

## 1.1.0 – 2024-08-05
### Added
- feat: madlad model support with ctranslate2 @kyteinsky
- ci: add docker build publish @kyteinsky


## 1.0.0 – 2024-02-23
### Added
* the app @marcelklehr
