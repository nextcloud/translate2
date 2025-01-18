#
# SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: MIT
#
"""Translation service"""

import json
import logging
import os
import threading
from copy import deepcopy
from typing import TypedDict

import ctranslate2
from sentencepiece import SentencePieceProcessor
from lib.util import clean_text


GPU_ACCELERATED = os.getenv("COMPUTE_DEVICE", "CPU") != "CPU"

logger = logging.getLogger(__name__)

class TranslateRequest(TypedDict):
    origin_language: str
    input: str
    target_language: str


if os.getenv("CI") is not None:
    ctranslate2.set_random_seed(420)


#Removed the translate_context function for initializing tokenizer and translator directly in the Service class.
#This avoids recreating them for every translation request.

class Service:
    def __init__(self, config: dict):
        self._lock=threading.Lock() # Used a threading lock here
        #to ensure thread safety when processing concurrent translation requests.
        global logger
        try:
            # The new approach ensures log_level supports both string and numeric values with default fallback to INFO.
            log_level = config.get("log_level", logging.INFO)
            if isinstance(log_level, str):
                log_level = getattr(logging, log_level.upper(), logging.INFO)
            logger.setLevel(log_level)

            ctranslate2.set_log_level(log_level)
            logger.setLevel(log_level)
            self.load_config(config)

            self.tokenizer= SentencePieceProcessor()
            self.tokenizer.Load(os.path.join(self.config["loader"]["model_path"],config["tokenizer_file"]))

            self.translator = ctranslate2.Translator(
            **{
                "device": "cuda" if GPU_ACCELERATED else "cpu",
                **self.config["loader"],
               }
            )

            # Resolve the path to 'languages.json' relative to the project root.
            languages_path = os.path.join(os.path.dirname(__file__), "..", "languages.json")
            if not os.path.exists(languages_path):
                raise FileNotFoundError(f"languages.json not found at {languages_path}")

            with open(languages_path) as f:
                self.languages = json.loads(f.read())
        except Exception as e:
            raise Exception(
                "Error reading languages list, ensure languages.json is present in the project root"
            ) from e

    def get_languages(self) -> dict[str, str]:
        return self.languages

    def load_config(self, config: dict):
        config_copy = deepcopy(config)

        if "model_name" in config_copy["loader"]:
            model_name = config_copy["loader"].pop("model_name")
            resolved_model_path = os.path.join("models", model_name.replace("/", "_"))
            if not os.path.exists(resolved_model_path):
                raise Exception(
                    f"Model '{model_name}' not found.Please download or set up the model at {resolved_model_path}."
                    )
            config_copy["loader"]["model_path"] = resolved_model_path
        elif "model_path" not in config_copy["loader"]:
            raise KeyError(
                "The configuration must contain either 'model_name' or 'model_path' under the 'loader' key."
                )
        self.config = config_copy



    def translate(self, data: TranslateRequest) -> str:

        logger.debug(f"translating text to: {data['target_language']}")

        with self._lock:
            input_tokens = self.tokenizer.Encode(
                f"<2{data['target_language']}> {clean_text(data['input'])}",
                out_type=str
                )
            results = self.translator.translate_batch(
                [input_tokens],
                batch_type="tokens",
                **self.config["inference"],
            )

            if len(results) == 0 or len(results[0].hypotheses) == 0:
                raise Exception("Empty result returned from translator")


            translation = self.tokenizer.Decode(results[0].hypotheses[0])
        logger.debug(f"Translated string: {translation}")
        return translation

    def close(self):
        # Cleanup resources during service shutdown.
        del self.tokenizer
        del self.translator
        logger.info("Service resources released.")
