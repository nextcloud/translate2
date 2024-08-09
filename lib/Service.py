"""Translation service"""

import json
import logging
import os
from contextlib import contextmanager
from copy import deepcopy
from time import perf_counter
from typing import TypedDict

import ctranslate2
from sentencepiece import SentencePieceProcessor
from util import clean_text

GPU_ACCELERATED = os.getenv("COMPUTE_DEVICE", "cuda") != "cpu"

logger = logging.getLogger(__name__)

class TranslateRequest(TypedDict):
    origin_language: str
    input: str
    target_language: str


if os.getenv("CI") is not None:
    ctranslate2.set_random_seed(420)


@contextmanager
def translate_context(config: dict):
    try:
        tokenizer = SentencePieceProcessor()
        tokenizer.Load(os.path.join(config["loader"]["model_path"], config["tokenizer_file"]))

        translator = ctranslate2.Translator(
            **{
                "device": "cuda" if GPU_ACCELERATED else "cpu",
                **config["loader"],
            }
        )
    except KeyError as e:
        raise Exception("Incorrect config file") from e
    except Exception as e:
        raise Exception("Error loading the translation model") from e

    try:
        start = perf_counter()
        yield (tokenizer, translator)
        elapsed = perf_counter() - start
        logger.info(f"time taken: {elapsed:.2f}s")
    except Exception as e:
        raise Exception("Error translating the input text") from e
    finally:
        del tokenizer
        # todo: offload to cpu?
        del translator


class Service:
    def __init__(self, config: dict):
        global logger
        try:
            self.load_config(config)
            ctranslate2.set_log_level(config["log_level"])
            logger.setLevel(config["log_level"])

            with open("languages.json") as f:
                self.languages = json.loads(f.read())
        except Exception as e:
            raise Exception(
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

    def translate(self, data: TranslateRequest) -> str:
        logger.debug(f"translating text to: {data['target_language']}")

        with translate_context(self.config) as (tokenizer, translator):
            input_tokens = tokenizer.Encode(f"<2{data['target_language']}> {clean_text(data['input'])}", out_type=str)
            results = translator.translate_batch(
                [input_tokens],
                batch_type="tokens",
                **self.config["inference"],
            )

            if len(results) == 0 or len(results[0].hypotheses) == 0:
                raise Exception("Empty result returned from translator")

            # todo: handle multiple hypotheses
            translation = tokenizer.Decode(results[0].hypotheses[0])

        logger.debug(f"Translated string: {translation}")
        return translation
