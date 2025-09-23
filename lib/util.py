#
# SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: MIT
#
"""Utility functions"""

import json
import os
import re

from nc_py_api.ex_app import persistent_storage

CONFIG_FILENAME = "config.json"

def clean_text(text: str) -> str:
    return re.sub(r"(\r?\n)+", " ", text).strip()


def get_config_path() -> str:
    # if the persistent storage contains a config file, return its path
    if os.path.exists(os.path.join(persistent_storage(), CONFIG_FILENAME)):
        return os.path.join(persistent_storage(), CONFIG_FILENAME)
    # else return default path
    return CONFIG_FILENAME


def load_config_file() -> dict:
    with open(get_config_path()) as f:
        config = json.loads(f.read())
        if "model_name" in config["loader"] and "model_path" in config["loader"]:
            raise Exception("Both 'model_name' and 'model_path' keys are present in the config. Please remove one of them.")  # noqa: E501
        if "model_name" not in config["loader"] and "model_path" not in config["loader"]:
            raise Exception("Neither 'model_name' nor 'model_path' keys are present in the config. Please add one of them.")  # noqa: E501
    return config


def save_config_file(config: dict) -> None:
    with open(get_config_path(), "w") as f:
        f.write(json.dumps(config, indent=4))
