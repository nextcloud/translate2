"""Translation service"""

import json
import logging
import os
import re
from contextlib import contextmanager
from time import perf_counter

import ctranslate2
from sentencepiece import SentencePieceProcessor

GPU_ACCELERATED = os.getenv("COMPUTE_DEVICE", "cuda") != "cpu"

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    return re.sub(r"(\r?\n)+", " ", text).strip()


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

    start = perf_counter()
    yield (tokenizer, translator)
    elapsed = perf_counter() - start

    logger.info(f"time taken: {elapsed:.2f}s")
    del tokenizer
    # todo: offload to cpu?
    del translator


class Service:
    def __init__(self, config: dict):
        global logger
        try:
            self.config = config
            ctranslate2.set_log_level(config["log_level"])
            logger.setLevel(config["log_level"])

            with open("languages.json") as f:
                self.languages = json.loads(f.read())
        except Exception as e:
            raise Exception(
                "Error reading languages list, ensure languages.json is present in the project root"
            ) from e

    def get_lang_names(self):
        return self.languages

    def translate(self, to_language: str, text: str) -> str:
        logger.debug(f"translating text to: {to_language}")

        with translate_context(self.config) as (tokenizer, translator):
            input_tokens = tokenizer.Encode(f"<2{to_language}> {clean_text(text)}", out_type=str)
            results = translator.translate_batch(
                [input_tokens],
                batch_type="tokens",
                **self.config["inference"],
            )

            if len(results) == 0 or len(results[0].hypotheses) == 0:
                raise Exception("Empty result returned from translator")

            # todo: handle multiple hypotheses
            translation = tokenizer.Decode(results[0].hypotheses[0])

        logger.info(f"Translated string: {translation}")
        return translation
