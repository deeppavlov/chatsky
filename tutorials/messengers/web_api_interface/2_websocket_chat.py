# %% [markdown]
"""
# Web API: 2. WebSocket Chat

This tutorial shows how to create a Web chat on FastAPI using websockets.

You can see the result at http://127.0.0.1:8000/.

This tutorial is a modified version of the FastAPI tutorial on WebSockets:
https://fastapi.tiangolo.com/advanced/websockets/.

As mentioned in that tutorial,

> ... for this example, we'll use a very simple HTML document
> with some JavaScript, all inside a long string.
> This, of course, is not optimal and you wouldn't use it for production.

Here, %mddoclink(api,messengers.common.interface,CallbackMessengerInterface)
is used to process requests.

%mddoclink(api,script.core.message,Message) is used to represent text messages.
"""

# %pip install dff uvicorn fastapi

# %%
from dff.messengers.common.interface import CallbackMessengerInterface
from dff.script import Message
from dff.pipeline import Pipeline
from dff.utils.testing import TOY_SCRIPT_ARGS, is_interactive_mode

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse


# %%
messenger_interfaces = CallbackMessengerInterface()
pipeline = Pipeline.from_script(
    *TOY_SCRIPT_ARGS, messenger_interfaces=[messenger_interfaces]
)


# %%
app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now();
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"User: {data}")
            request = Message(data)
            context = await messenger_interfaces.on_request_async(
                request, client_id
            )
            response = context.last_response.text
            if response is not None:
                await websocket.send_text(f"Bot: {response}")
            else:
                await websocket.send_text("Bot did not return text.")
    except WebSocketDisconnect:  # ignore disconnections
        pass


# %%
if __name__ == "__main__":
    if is_interactive_mode():  # do not run this during doc building
        pipeline.run()
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
        )
