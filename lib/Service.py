#
# SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: MIT
#
"""Translation service"""

import json
import logging
import os
import re
from copy import deepcopy
from time import perf_counter
from typing import TypedDict

import ctranslate2
from nc_py_api.ex_app import setup_nextcloud_logging
from sentencepiece import SentencePieceProcessor
from util import clean_text

logger = logging.getLogger(os.environ["APP_ID"] + __name__)

# Languages that do not use spaces between words
_NO_SPACE_LANGUAGES = {"zh", "yue", "ja", "th", "my", "km", "lo", "bo", "dz", "shn"}


def _is_no_space_text(text: str) -> bool:
    """Return True when the source text appears to use a no-space writing system.

    Since the origin language is always "detect_language",
    we inspect the text itself. A whitespace ratio below 5% is
    treated as no-space text, which helps identify languages
    such as Chinese, Japanese, Thai, and few more.
    """
    stripped = text.strip()
    if not stripped:
        return False
    space_count = stripped.count(" ") + stripped.count("\t") + stripped.count("\n")
    return (space_count / len(stripped)) < 0.05


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

    def _chunk_text(self, text: str, max_units: int, is_no_space: bool = False) -> list[str]:
        """Split text into sentence-boundary chunks of a maximum size.

        Space-delimited text is split by words, while no-space text is split by
        characters. Sentence boundaries are preserved where possible, using
        standard punctuation for space-delimited text and
        CJK (Chinese, Japanese, and Korean-alike languages) punctuation for no-space text.
        """
        # Keep sentence punctuation attached to the preceding sentence.
        # For no-space text (CJK etc.) use `\s*` because sentences run together without
        # whitespace. For all other text use `\s+`.
        sentences = (
            re.split(r"(?<=[\u3002\uff01\uff1f])\s*", text)
            if is_no_space
            else re.split(r"(?<=[.!?])\s+", text)
        )

        chunks: list[str] = []
        current_parts: list[str] = []
        current_count = 0
        sep = "" if is_no_space else " "

        for sentence in sentences:
            unit_count = len(sentence) if is_no_space else len(sentence.split())
            if unit_count == 0:
                continue

            if current_count + unit_count > max_units and current_parts:
                chunks.append(sep.join(current_parts))
                current_parts = []
                current_count = 0

            if unit_count > max_units:
                if is_no_space:
                    for i in range(0, len(sentence), max_units):
                        chunks.append(sentence[i:i + max_units])
                else:
                    words = sentence.split()
                    for i in range(0, len(words), max_units):
                        chunks.append(" ".join(words[i:i + max_units]))
                continue

            current_parts.append(sentence)
            current_count += unit_count

        if current_parts:
            chunks.append(sep.join(current_parts))

        return chunks if chunks else [text]

    def _join_chunks(self, chunks: list[str], target_language: str) -> str:
        """Join translated chunks respecting language-specific rules.

        No-space languages are joined without a separator, while other languages
        use a space. The translated chunks are already in the correct reading
        order, so their order should not be reversed.
        """
        chunks = [c.strip() for c in chunks if c.strip()]
        if not chunks:
            return ""

        target_base = target_language.split("_")[0].lower()

        separator = "" if target_base in _NO_SPACE_LANGUAGES else " "
        return separator.join(chunks)

    def translate(self, data: TranslateRequest) -> str:
        logger.debug(f"translating text to: {data['target_language']}")

        try:
            start = perf_counter()
            cleaned = clean_text(data["input"])
            chunking = self.config.get("chunking", {})
            chunk_threshold = chunking.get("chunk_threshold", 256)
            chunk_size = chunking.get("chunk_size", 80)
            is_no_space_source = _is_no_space_text(cleaned)
            input_token_count = len(self.tokenizer.Encode(cleaned, out_type=str))
            chunks = (
                self._chunk_text(cleaned, chunk_size, is_no_space=is_no_space_source)
                if input_token_count > chunk_threshold
                else [cleaned]
            )

            all_input_tokens = [
                self.tokenizer.Encode(
                    f"<2{data['target_language']}> {chunk}",
                    out_type=str,
                )
                for chunk in chunks
            ]

            inference_config = dict(self.config["inference"])

            results = list(self.translator.translate_iterable(
                all_input_tokens,
                batch_type="tokens",
                **inference_config,
            ))

            if len(results) != len(chunks) or any(len(r.hypotheses) == 0 for r in results):
                raise ServiceException("Empty result returned from translator")

            # todo: handle multiple hypotheses
            translated_chunks = [self.tokenizer.Decode(r.hypotheses[0]) for r in results]

            translation = self._join_chunks(translated_chunks, data["target_language"])
            elapsed = perf_counter() - start
            logger.info(f"time taken: {elapsed:.2f}s")
        except Exception as e:
            raise ServiceException("Error translating the input text") from e

        logger.debug(f"Translated string: {translation}")
        return translation
