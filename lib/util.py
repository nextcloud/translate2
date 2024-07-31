"""Utility functions"""

import json
import re


def clean_text(text: str) -> str:
    return re.sub(r"(\r?\n)+", " ", text).strip()


def load_config_file(path: str = "config.json") -> dict:
    with open(path) as f:
        config = json.loads(f.read())
        if "model_name" in config["loader"] and "model_path" in config["loader"]:
            raise Exception("Both 'model_name' and 'model_path' keys are present in the config. Please remove one of them.")  # noqa: E501
        if "model_name" not in config["loader"] and "model_path" not in config["loader"]:
            raise Exception("Neither 'model_name' nor 'model_path' keys are present in the config. Please add one of them.")  # noqa: E501
    return config


def save_config_file(config: dict, path: str = "config.json") -> None:
    with open(path, "w") as f:
        f.write(json.dumps(config, indent=4))

