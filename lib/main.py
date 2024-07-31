"""The main module of the translate2 app"""

import logging
import os
import queue
import threading
import typing
from contextlib import asynccontextmanager

import uvicorn.logging
from dotenv import load_dotenv
from fastapi import Body, FastAPI, Request, responses
from nc_py_api import AsyncNextcloudApp, NextcloudApp
from nc_py_api.ex_app import LogLvl, run_app, set_handlers
from Service import Service
from util import load_config_file, save_config_file

load_dotenv()

config = load_config_file()

# logging config
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(config["log_level"])


class ModelConfig(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if key == "path":
            config["loader"]["hf_model_path"] = value
            service.load_config(config)
            save_config_file(config)

        super().__setitem__(key, value)


# download models if "model_name" key is present in the config
models_to_fetch = None
cache_dir = os.getenv("APP_PERSISTENT_STORAGE", "models/")
if "model_name" in config["loader"]:
    models_to_fetch = { config["loader"]["model_name"]: ModelConfig({ "cache_dir": cache_dir }) }


@asynccontextmanager
async def lifespan(_: FastAPI):
    set_handlers(
        fast_api_app=APP,
        enabled_handler=enabled_handler,
        models_to_fetch=models_to_fetch,
    )
    t = BackgroundProcessTask()
    t.start()
    yield


APP = FastAPI(lifespan=lifespan)
TASK_LIST: queue.Queue = queue.Queue(maxsize=100)
service = Service(config)


@APP.exception_handler(Exception)
async def _(request: Request, exc: Exception):
    logger.error("Error processing request", request.url.path, exc)

    task: dict | None = getattr(exc, "args", None)

    nc = NextcloudApp()
    nc.log(LogLvl.ERROR, str(exc))
    if task:
        nc.providers.translations.report_result(task["id"], error=str(exc))

    return responses.JSONResponse({
        "error": "An error occurred while processing the request, please check the logs for more info"
    }, 500)


class BackgroundProcessTask(threading.Thread):
    def run(self, *args, **kwargs):  # pylint: disable=unused-argument
        while True:
            task = TASK_LIST.get(block=True)
            try:
                translation = service.translate(task["to_language"], task["text"])
                NextcloudApp().providers.translations.report_result(
                    task_id=task["id"],
                    result=str(translation).strip(),
                )
            except Exception as e:  # noqa
                e.args = task
                raise e


@APP.post("/translate")
async def tiny_llama(
    from_language: typing.Annotated[str, Body()],
    to_language: typing.Annotated[str, Body()],
    text: typing.Annotated[str, Body()],
    task_id: typing.Annotated[int, Body()],
):
    try:
        task = {
            "text": text,
            "from_language": from_language,
            "to_language": to_language,
            "id": task_id,
        }
        logger.debug(task)
        TASK_LIST.put(task)
    except queue.Full:
        return responses.JSONResponse(content={"error": "task queue is full"}, status_code=429)
    return responses.Response()


async def enabled_handler(enabled: bool, nc: AsyncNextcloudApp) -> str:
    print(f"enabled={enabled}")
    if enabled is True:
        languages = service.get_lang_names()
        logger.info(
            "Supported languages short list", {
                "count": len(languages),
                "languages": list(languages.keys())[:10],
            }
        )
        await nc.providers.translations.register(
            "translate2",
            "Local Machine Translation",
            "/translate",
            languages,
            languages,
        )
    else:
        await nc.providers.speech_to_text.unregister("translate2")
    return ""


if __name__ == "__main__":
    uvicorn_log_level = uvicorn.logging.TRACE_LOG_LEVEL if config["log_level"] == logging.DEBUG else config["log_level"]
    run_app("main:APP", log_level=uvicorn_log_level)
