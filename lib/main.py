#
# SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: MIT
#
"""The main module of the translate2 app"""

import logging
import os
import threading
import traceback
from contextlib import asynccontextmanager, suppress
from json import JSONDecodeError
from time import sleep

import httpx
import uvicorn.logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, responses
from nc_py_api import AsyncNextcloudApp, NextcloudApp, NextcloudException
from nc_py_api.ex_app import LogLvl, run_app, set_handlers, setup_nextcloud_logging
from nc_py_api.ex_app.integration_fastapi import fetch_models_task
from nc_py_api.ex_app.providers.task_processing import ShapeEnumValue, TaskProcessingProvider
from Service import Service, ServiceException, TranslateRequest
from util import load_config_file, save_config_file

load_dotenv()

config = load_config_file()

# logging config
logging.basicConfig()
logger = logging.getLogger(os.environ["APP_ID"] + __name__)
logger.setLevel(config["log_level"])
setup_nextcloud_logging(os.environ["APP_ID"] + "_" + __name__, config["log_level"])


class ModelConfig(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if key == "path":
            config["loader"]["hf_model_path"] = value
            save_config_file(config)

        super().__setitem__(key, value)


# download models if "model_name" key is present in the config
models_to_fetch = None
cache_dir = os.getenv("APP_PERSISTENT_STORAGE", "models/")
if "model_name" in config["loader"]:
    models_to_fetch = { config["loader"]["model_name"]: ModelConfig({ "cache_dir": cache_dir }) }


app_enabled = threading.Event()
@asynccontextmanager
async def lifespan(_: FastAPI):
    global app_enabled
    set_handlers(
        fast_api_app=APP,
        enabled_handler=enabled_handler,  # type: ignore
        models_to_fetch=models_to_fetch,  # type: ignore
    )

    nc = NextcloudApp()
    if nc.enabled_state:
        app_enabled.set()
        if "hf_model_path" not in config["loader"] and "model_path" not in config["loader"]:
            with suppress(NextcloudException):
                fetch_models_task(nc, models_to_fetch, 50)  # pyright: ignore[reportArgumentType]
        worker = threading.Thread(target=task_fetch_thread, args=(Service(config),))
        worker.start()

    yield
    app_enabled.clear()


APP_ID = "translate2"
TASK_TYPE_ID = "core:text2text:translate"
IDLE_POLLING_INTERVAL = config["idle_polling_interval"]
DETECT_LANGUAGE = ShapeEnumValue(name="Detect Language", value="auto")
APP = FastAPI(lifespan=lifespan)


def report_error(task: dict | None, exc: Exception):
    try:
        traceback.print_exc()
        nc = NextcloudApp()
        nc.log(LogLvl.ERROR, str(exc))
        if task:
            nc.providers.task_processing.report_result(
                task["id"],
                error_message=f"Error translating the input text: {exc}"
            )
    except (NextcloudException, httpx.NetworkError) as e:
        logger.error(f"Error reporting error to the server: {e}")


@APP.exception_handler(ServiceException)
async def _(request: Request, exc: ServiceException):
    logger.error("Error processing request", request.url.path, exc)
    report_error(None, exc)

    return responses.JSONResponse({ "error": str(exc) }, 500)


@APP.exception_handler(Exception)
async def _(request: Request, exc: Exception):
    logger.error("Unknown error processing request", request.url.path, exc)
    report_error(None, exc)

    return responses.JSONResponse({
        "error": "An error occurred while processing the translation request"
    }, 500)


def task_fetch_thread(service: Service):
    global app_enabled

    nc = NextcloudApp()
    while True:
        if not app_enabled.is_set():
            logger.debug("Shutting down task fetch worker, app not enabled")
            break

        try:
            task = nc.providers.task_processing.next_task([APP_ID], [TASK_TYPE_ID])
        except (NextcloudException, JSONDecodeError) as e:
            logger.error("Error fetching the next task", exc_info=e)
            sleep(IDLE_POLLING_INTERVAL)
            continue
        except (
                httpx.RemoteProtocolError,
                httpx.ReadError,
                httpx.LocalProtocolError,
                httpx.PoolTimeout,
        ) as e:
            logger.debug("Ignored error during task polling", exc_info=e)
            sleep(IDLE_POLLING_INTERVAL / 2)
            continue

        if not task:
            logger.debug("No tasks found")
            sleep(IDLE_POLLING_INTERVAL)
            continue

        logger.debug(f"Processing task: {task}")

        input_ = task.get("task", {}).get("input")
        if input_ is None or not isinstance(input_, dict):
            logger.error("Invalid task object received, expected task object with input key")
            continue

        try:
            request = TranslateRequest(**input_)
            translation = service.translate(request)
            try:
                nc.providers.task_processing.report_result(
                    task_id=task["task"]["id"],
                    output={"output": translation},
                )
            except Exception: # Retries when a failure occurs and creates a new NextcloudApp instance
                nc = NextcloudApp()
                nc.providers.task_processing.report_result(
                    task_id=task["task"]["id"],
                    output={"output": translation},
                )
        except Exception as e: # This will also catch the retry for reporting the result
            report_error(task, e)


async def enabled_handler(enabled: bool, nc: AsyncNextcloudApp) -> str:
    global app_enabled
    print(f"enabled={enabled}")

    service = Service(config)

    if not enabled:
        try:
            await nc.providers.task_processing.unregister(APP_ID)
            app_enabled.clear()
            return ""
        except Exception as e:
            logger.error(f"Error unregistering the app: {e}")
            return f"Error unregistering the app: {e}"

    languages = [
        ShapeEnumValue(name=lang_name, value=lang_id)
        for lang_id, lang_name in service.get_languages().items()
    ]

    provider = TaskProcessingProvider(
        id=APP_ID,
        name="Local Machine Translation",
        task_type=TASK_TYPE_ID,
        input_shape_enum_values={
            "origin_language": [DETECT_LANGUAGE],
            "target_language": languages,
        },
        input_shape_defaults={
            "origin_language": DETECT_LANGUAGE.value,
        },
    )
    try:
        await nc.providers.task_processing.register(provider)
    except Exception as e:
        logger.error(f"Error registering the app: {e}")
        return f"Error registering the app: {e}"

    if not app_enabled.is_set():
        app_enabled.set()
        worker = threading.Thread(target=task_fetch_thread, args=(service,))
        worker.start()

    return ""


if __name__ == "__main__":
    uvicorn_log_level = (
        uvicorn.logging.TRACE_LOG_LEVEL
        if config["log_level"] == logging.DEBUG
        else config["log_level"]
    )
    run_app("main:APP", log_level=uvicorn_log_level)
