"""The main module of the translate2 app"""

import queue
import threading
import typing
from contextlib import asynccontextmanager

# todo
from dotenv import load_dotenv
from fastapi import Body, FastAPI, Request, responses
from nc_py_api import AsyncNextcloudApp, NextcloudApp
from nc_py_api.ex_app import LogLvl, run_app, set_handlers
from Service import LoaderException, Service

# todo
load_dotenv()

service = Service()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    set_handlers(
        APP,
        enabled_handler,
    )
    t = BackgroundProcessTask()
    t.start()
    yield


APP = FastAPI(lifespan=lifespan)
TASK_LIST: queue.Queue = queue.Queue(maxsize=100)


@APP.exception_handler(LoaderException)
async def _(request: Request, exc: LoaderException):
    print(f"Loader Error: {request.url.path}:", exc)
    return responses.JSONResponse({
        "error": "The resource loader is facing some issues, please check the logs for more info"
    }, 500)


class BackgroundProcessTask(threading.Thread):
    def run(self, *args, **kwargs):  # pylint: disable=unused-argument
        while True:
            task = TASK_LIST.get(block=True)
            try:
                translation = service.translate(task["model"], task["to_language"], task["text"])
                NextcloudApp().providers.translations.report_result(
                    task_id=task["id"],
                    result=str(translation).strip(),
                )
            except Exception as e:  # noqa
                print(str(e))
                nc = NextcloudApp()
                nc.log(LogLvl.ERROR, str(e))
                nc.providers.translations.report_result(task["id"], error=str(e))



@APP.post("/translate")
async def tiny_llama(
    name: typing.Annotated[str, Body()],
    from_language: typing.Annotated[str, Body()],
    to_language: typing.Annotated[str, Body()],
    text: typing.Annotated[str, Body()],
    task_id: typing.Annotated[int, Body()],
):
    try:
        task = {
            "model": name[11:],
            "text": text,
            "from_language": from_language,
            "to_language": to_language,
            "id": task_id,
        }
        print(task)
        TASK_LIST.put(task)
    except queue.Full:
        return responses.JSONResponse(content={"error": "task queue is full"}, status_code=429)
    return responses.Response()


async def enabled_handler(enabled: bool, nc: AsyncNextcloudApp) -> str:
    print(f"enabled={enabled}")
    if enabled is True:
        models = service.get_models()

        for (model_name, languages) in models:
            print(
                f"Supported languages in model {model_name}: ({len(languages)}): {list(languages.values())[:10]}, ..."
            )
            await nc.providers.translations.register(
                f"translate2:{model_name}",
                "Local Machine Translation",
                "/translate",
                languages,
                languages,
            )
    else:
        await nc.providers.speech_to_text.unregister("translate2")
    return ""


if __name__ == "__main__":
    run_app("main:APP", log_level="trace")
