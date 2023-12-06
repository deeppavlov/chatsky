import os
from bot.pipeline import pipeline

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from dff.script import Message, Context


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


if __name__ == "__main__":
    interface_type = os.getenv("INTERFACE")
    if interface_type == "web":
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
        )
    else:
        pipeline.run()
