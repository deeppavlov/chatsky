import os
import asyncio
from bot.pipeline import pipeline

import uvicorn
from telebot import types
from dff.messengers.telegram.messenger import TelegramMessenger
from dff.messengers.telegram.interface import extract_telegram_request_and_id
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse
from dff.script import Message, Context

HOST = os.getenv("HOST", "0.0.0.0")
PORT = 8000
FULL_URI = f"https://{HOST}:{PORT}/telegram"
telegram_token = os.getenv("TELEGRAM_TOKEN")

app = FastAPI()


@app.get("/")
async def index():
    return FileResponse("static/index.html", media_type="text/html")


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    # store user info in the dialogue context
    await pipeline.context_storage.set_item_async(
        client_id, Context(id=client_id, misc={"ip": websocket.client.host, "headers": websocket.headers.raw})
    )

    async def respond(request: Message):
        context = await pipeline._run_pipeline(request, client_id)
        response = context.last_response.text
        await websocket.send_text(response)
        return context

    try:
        await respond(Message())  # display welcome message

        while True:
            data = await websocket.receive_text()
            await respond(Message(text=data))
    except WebSocketDisconnect:  # ignore disconnects
        pass


if telegram_token is not None:
    messenger = TelegramMessenger(telegram_token)
    messenger.remove_webhook()
    messenger.set_webhook(FULL_URI)

    @app.post("/telegram")
    async def endpoint(request: Request):
        json_string = (await request.body()).decode("utf-8")
        update = types.Update.de_json(json_string)
        request, ctx_id = extract_telegram_request_and_id(update, messenger)
        resp = asyncio.run(pipeline(request, ctx_id))
        messenger.send_response(resp.id, resp.last_response)
        return ""


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
    )
