#
# SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: MIT
#
"""Translation service"""

import json
import logging
import os
from copy import deepcopy
from time import perf_counter
from typing import TypedDict

import ctranslate2
from nc_py_api.ex_app import setup_nextcloud_logging
from sentencepiece import SentencePieceProcessor
from util import clean_text

logger = logging.getLogger(os.environ["APP_ID"] + __name__)

class ServiceException(Exception):
    pass


class TranslateRequest(TypedDict):
    origin_language: str
    input: str
    target_language: str


if os.getenv("CI") is not None:
    ctranslate2.set_random_seed(420)


class Service:
    def __init__(self, config: dict):
        global logger
        try:
            self.load_config(config)
            ctranslate2.set_log_level(config["log_level"])
            logger.setLevel(config["log_level"])
            setup_nextcloud_logging(os.environ["APP_ID"] + "_" + __name__, config["log_level"])

            with open("languages.json") as f:
                self.languages = json.loads(f.read())
        except Exception as e:
            raise ServiceException(
                "Error reading languages list, ensure languages.json is present in the project root"
            ) from e

    def get_languages(self) -> dict[str, str]:
        return self.languages

    def load_config(self, config: dict):
        config_copy = deepcopy(config)
        config_copy["loader"].pop("model_name", None)

        if "hf_model_path" in config_copy["loader"]:
            config_copy["loader"]["model_path"] = config_copy["loader"].pop("hf_model_path")

        self.config = config_copy

    def load_model(self):
        try:
            self.tokenizer = SentencePieceProcessor()
            self.tokenizer.Load(os.path.join(self.config["loader"]["model_path"], self.config["tokenizer_file"]))

            self.translator = ctranslate2.Translator(
                **{
                    "device": "cuda" if os.getenv("COMPUTE_DEVICE") == "CUDA" else "cpu",
                    **self.config["loader"],
                }
            )
        except KeyError as e:
            raise ServiceException(
                "Incorrect config file, ensure all required keys are present from the default config"
            ) from e
        except Exception as e:
            raise ServiceException("Error loading the translation model") from e

    def translate(self, data: TranslateRequest) -> str:
        logger.debug(f"translating text to: {data['target_language']}")

        try:
            start = perf_counter()
            input_tokens = self.tokenizer.Encode(
                f"<2{data['target_language']}> {clean_text(data['input'])}",
                out_type=str,
            )
            results = self.translator.translate_batch(
                [input_tokens],
                batch_type="tokens",
                **self.config["inference"],
            )

            if len(results) == 0 or len(results[0].hypotheses) == 0:
                raise ServiceException("Empty result returned from translator")

            # todo: handle multiple hypotheses
            translation = self.tokenizer.Decode(results[0].hypotheses[0])
            elapsed = perf_counter() - start
            logger.info(f"time taken: {elapsed:.2f}s")
        except Exception as e:
            raise ServiceException("Error translating the input text") from e

        logger.debug(f"Translated string: {translation}")
        return translation
