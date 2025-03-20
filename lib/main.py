#
# SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: MIT
#

"""The main module of the translate2 app"""
import os
import logging
import threading
import traceback
from contextlib import asynccontextmanager
from time import sleep

import httpx
import uvicorn.logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, responses
from nc_py_api import AsyncNextcloudApp, NextcloudApp, NextcloudException
from nc_py_api.ex_app import LogLvl, run_app, set_handlers
from nc_py_api.ex_app.providers.task_processing import ShapeEnumValue, TaskProcessingProvider

#Instead of  "from Service import Service, TranslateRequest" used "from lib.Service import Service, TranslateRequest"
from lib.Service import Service, TranslateRequest
from lib.util import load_config_file

import concurrent.futures


load_dotenv()

config = load_config_file()



# logging config
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(config["log_level"])


# Removed ModelConfig and Simplified code by directly handling model configuration with the config dictionary.

# download models if "model_name" key is present in the config
models_to_fetch = None
cache_dir = os.getenv("APP_PERSISTENT_STORAGE", "models/")
if "model_name" in config["loader"]:
    models_to_fetch = { config["loader"]["model_name"]: { "cache_dir": cache_dir } }


app_enabled = threading.Event()
@asynccontextmanager
async def lifespan(_: FastAPI):
    global app_enabled
    service= Service(config)
    try:
        set_handlers(
            fast_api_app=APP,
            enabled_handler=enabled_handler,  # type: ignore
            models_to_fetch=models_to_fetch,  # type: ignore
        )

        nc = NextcloudApp()
        if nc.enabled_state:
            app_enabled.set()
            worker = threading.Thread(target=task_fetch_thread, args=(service,))
            worker.start()

        yield
    finally:
        #clean up the Service instance and background workers.
        app_enabled.clear()
        service.close()


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


@APP.exception_handler(Exception)
async def _(request: Request, exc: Exception):
    logger.error("Error processing request", request.url.path, exc)
    report_error(None, exc)

    return responses.JSONResponse({
        "error": "An error occurred while processing the request, please check the logs for more info"
    }, 500)


def task_fetch_thread(service: Service):
    global app_enabled

    nc = NextcloudApp()
    #Used a thread pool for concurrent processing.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        while True:
            if not app_enabled.is_set():
                logger.debug("Shutting down task fetch worker, app not enabled")
                break

            try:
                task = nc.providers.task_processing.next_task([APP_ID], [TASK_TYPE_ID])
            except Exception as e:
                logger.error(f"Error fetching task: {e}")
                sleep(IDLE_POLLING_INTERVAL)
                continue

            if not task:
                logger.debug(f"No tasks found. Sleeping for {IDLE_POLLING_INTERVAL}s")
                sleep(IDLE_POLLING_INTERVAL)
                continue

            logger.debug(f"Processing task: {task}")

            input_ = task.get("task", {}).get("input")
            if input_ is None or not isinstance(input_, dict):
                logger.error("Invalid task object received, expected task object with input key")
                continue

            try:
                request = TranslateRequest(**input_)
                executor.submit(process_task, service, nc, task, request)
            except Exception as e:
                logger.error(f"Error submitting task to executor: {e}")
                report_error(task, e)

def process_task(service: Service, nc: NextcloudApp, task: dict, request: TranslateRequest):
    try:
        translation = service.translate(request)
        nc.providers.task_processing.report_result(
            task_id=task["task"]["id"],
            output={"output": translation},
        )
        logger.info(f"Successfully processed task {task['task']['id']}")
    except NextcloudException as e:
        logger.error(f"Nextcloud exception while reporting result: {e}")
        report_error(task, e)
    except Exception as e:
        report_error(task, e)

enabled_lock = threading.Lock()

async def enabled_handler(enabled: bool, nc: AsyncNextcloudApp) -> str:
    global app_enabled
    print(f"enabled={enabled}")

    service = Service(config)

    if not enabled:
        try:
            await nc.providers.task_processing.unregister(APP_ID)
            app_enabled.clear()
        except Exception as e:
            logger.error(f"Error unregistering the app: {e}")

        return ""

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
        return ""

    if not app_enabled.is_set():
        app_enabled.set()
        if not hasattr(service, "_worker"):
            service._worker = threading.Thread(target=task_fetch_thread, args=(service,))
            service._worker.start()

    return ""


if __name__ == "__main__":
    uvicorn_log_level = (
        uvicorn.logging.TRACE_LOG_LEVEL
        if config["log_level"] == logging.DEBUG
        else config["log_level"]
    )
    run_app("main:APP", log_level=uvicorn_log_level)
