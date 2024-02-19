"""Tha main module of the translate2 app
"""

import queue
import threading
import typing
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, responses, Body
from nc_py_api import AsyncNextcloudApp, NextcloudApp
from nc_py_api.ex_app import LogLvl, anc_app, run_app, set_handlers
import torch
from Service import Service

cuda = torch.cuda.is_available()
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


class BackgroundProcessTask(threading.Thread):
    def run(self, *args, **kwargs):  # pylint: disable=unused-argument
        while True:
            task = TASK_LIST.get(block=True)
            try:
                translation = service.translate(task.get("from_language"), task.get("to_language"), task.get("text"))
                NextcloudApp().providers.translations.report_result(
                    task_id=task["id"],
                    result=str(translation),
                )
            except Exception as e:  # noqa
                print(str(e))
                nc = NextcloudApp()
                nc.log(LogLvl.ERROR, str(e))
                nc.providers.translations.report_result(task["id"], error=str(e))



@APP.post("/translate")
async def tiny_llama(
    _nc: typing.Annotated[AsyncNextcloudApp, Depends(anc_app)],
    from_language: typing.Annotated[str, Body()],
    to_language: typing.Annotated[str, Body()],
    text: typing.Annotated[str, Body()],
    task_id: typing.Annotated[int, Body()],
):
    try:
        print({"text": text, "from_language": from_language, "to_language": to_language, "id": task_id})
        TASK_LIST.put({"text": text, "from_language": from_language, "to_language": to_language, "id": task_id}, block=False)
    except queue.Full:
        return responses.JSONResponse(content={"error": "task queue is full"}, status_code=429)
    return responses.Response()


async def enabled_handler(enabled: bool, nc: AsyncNextcloudApp) -> str:
    print(f"enabled={enabled}")
    if enabled is True:
        from_languages, to_languages = service.get_langs()
        print(to_languages)
        print(from_languages)
        await nc.providers.translations.register('translate2', "Local Machine translation", '/translate', from_languages, to_languages)
    else:
        await nc.providers.speech_to_text.unregister('translate2')
    return ""




if __name__ == "__main__":
    run_app("main:APP", log_level="trace")
