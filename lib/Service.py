"""Translation service"""

import json
import os
from pathlib import Path
from time import perf_counter

from llama_cpp.llama import Llama


class LoaderException(Exception):
    pass


class LlamaContext:
    def __init__(self, model_name: str, gpu_accelerated: bool):
        try:
            with open("../config.json") as f:
                config = json.loads(f.read())["llama"][model_name]
                config["model_path"] = Path("../models/", config["model_name"])
                del config["model_name"]

            self.llama = Llama(n_gpu_layers=-1 if gpu_accelerated else 0, **config)
        except Exception as e:
            raise LoaderException(
                f"Error reading config, ensure config.json is present at {Path('..', os.getcwd())}"
            ) from e

    def __enter__(self):
        self.start = perf_counter()
        return self.llama

    def __exit__(self, exc_type, exc_value, exc_tb):
        print(f"time taken {perf_counter() - self.start}")
        del self.llama


class Service:
    gpu_accelerated = os.getenv("COMPUTE_DEVICE", "cuda") != "cpu"
    temperature = 0.1

    def __init__(self):
        try:
            with open("../languages.json") as f:
                self.languages = json.loads(f.read())
        except Exception as e:
            raise Exception(
                f"Error reading languages list, ensure languages.json is present at {Path('..', os.getcwd())}"
            ) from e

    def get_lang_names(self):
        return self.languages

    def get_models(self):
        models = []
        languages = self.get_lang_names()

        for file in os.scandir("../models/"):
            if os.path.isfile(file.path) and file.name.endswith(".gguf"):
                models.append((file.name, languages))

        return models

    def translate(self, model_name: str, to_language: str, text: str):
        print("translating text to", to_language)

        with LlamaContext(model_name, self.gpu_accelerated) as llama:
            translation = llama(f"<2{to_language}> {text}", temperature=self.temperature)

        print(translation)
        return translation.choices[0].text
