"""Translation service"""

import json
import os
import re
from contextlib import contextmanager
from time import perf_counter

from llama_cpp.llama import Llama

GPU_ACCELERATED = os.getenv("COMPUTE_DEVICE", "cuda") != "cpu"
TEMPERATURE = 0.1


class LoaderException(Exception):
    pass


def clean_text(text: str) -> str:
    return re.sub(r"(\r?\n)+", " ", text).strip()


@contextmanager
def llama_context():
    try:
        with open(os.path.join(os.getcwd(), "../config.json")) as f:
            # todo
            config = json.loads(f.read())["llama"]
            config["model_path"] = os.path.join(os.getcwd(), "../models/", config["model_file"])
            del config["model_file"]

        llama = Llama(n_gpu_layers=-1 if GPU_ACCELERATED else 0, **config)
    except Exception as e:
        raise LoaderException(
            "Error reading config, ensure config.json is present in the project root"
        ) from e

    start = perf_counter()
    yield llama
    elapsed = perf_counter() - start
    print(f"time taken: {elapsed:.2f} s")
    del llama


class Service:
    def __init__(self):
        try:
            with open("../languages.json") as f:
                self.languages = json.loads(f.read())
        except Exception as e:
            raise Exception(
                "Error reading languages list, ensure languages.json is present in the project root"
            ) from e

    def get_lang_names(self):
        return self.languages

    # def get_models(self):
    #     models = []
    #     languages = self.get_lang_names()

    #     for file in os.scandir("../models/"):
    #         if os.path.isfile(file.path) and file.name.endswith(".gguf"):
    #             models.append((file.name, languages))

    #     return models

    def translate(self, to_language: str, text: str):
        print("translating text to", to_language)

        with llama_context() as llama:
            translation = llama(f"<2{to_language}> {clean_text(text)}", temperature=TEMPERATURE)

        print(translation)
        return translation.choices[0].text
