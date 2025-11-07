<!--
  - SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: MIT
-->
# Nextcloud Local Machine Translation

[![REUSE status](https://api.reuse.software/badge/github.com/nextcloud/translate2)](https://api.reuse.software/info/github.com/nextcloud/translate2)

The *translate2* app provides machine translation functionality in Nextcloud and acts as a translation backend for the [Nextcloud Assistant app](https://apps.nextcloud.com/apps/assistant).
It runs only open weights models and does so entirely on-premises.

The app currently supports 400+ languages. See the complete list here: https://huggingface.co/datasets/allenai/MADLAD-400

**Requires [`AppAPI`](https://github.com/cloud-py-api/app_api) to work.**

For installation steps and other details, see https://docs.nextcloud.com/server/latest/admin_manual/ai/app_translate2.html
