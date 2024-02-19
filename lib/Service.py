import os
from time import perf_counter
from transformers import pipeline

class Service:
    dir_path = os.path.dirname(os.path.realpath(__file__))

    def get_lang_names(self):
        return {
            'de': 'German',
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'zh': 'Chinese',
            'it': 'Italian',
            'sv': 'Swedish',
            'ar': 'Arabic',
            'fi': 'Finnish',
            'nl': 'Dutch',
            'ja': 'Japanese',
            'tr': 'Turkish',
        }

    def get_models(self):
        models = []

        for file in os.scandir(self.dir_path + "/../models/"):
            if os.path.isdir(file.path):
                models.append(file.name)

        return models

    def get_langs(self):
        lang_names = self.get_lang_names()
        from_languages = {}
        to_languages = {}
        for model_name in self.get_models():
            [from_language, to_language] = model_name.split('-', 2)
            from_languages[from_language] = lang_names[from_language]
            to_languages[to_language] = lang_names[to_language]
        return from_languages, to_languages

    def translate(self, from_language, to_language, text):
        model_name = from_language + "-" + to_language
        print(f"model: {model_name}")

        if not model_name in self.get_models():
            if 'en-'+to_language in self.get_models() and from_language+'-en' in self.get_models():
                return self.translate('en', to_language, self.translate(from_language, 'en', text))

            raise Exception('Requested model is not available')

        translator = pipeline("translation", model=self.dir_path + "/../models/" + model_name)
        print("translating")
        start = perf_counter()
        translation = translator(text)
        print(f"time taken {perf_counter() - start}")
        print(translation)
        return translation[0]['translation_text']
