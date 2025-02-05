import time

try:
    import uvicorn
    from fastapi import FastAPI

    web_api_available = True
except ImportError as exc:
    web_api_available = False
    import_error = exc
from pydantic import BaseModel

from chatsky.core import Message
from chatsky.messengers.common import MessengerInterface


class HealthStatus(BaseModel):
    status: str
    uptime: float = None


class HTTPMessengerInterface(MessengerInterface):
    class ChatskyResponse(BaseModel):
        user_id: str
        response: Message

    def __init__(self, port: int):
        if not web_api_available:
            raise ImportError(
                "Some packages are missing.\nTry to run `pip install chatsky[web-api]`."
            ) from import_error
        super().__init__()
        self.port = port
        self.start_time = None

    def health_check(self):
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
        }

    async def connect(self, pipeline_runner):
        app = FastAPI()

        @app.post("/chat", response_model=self.ChatskyResponse)
        async def respond(user_id: str, user_message: str):
            message = Message(text=user_message)
            context = await pipeline_runner(message, user_id)
            return {"user_id": user_id, "response": context.last_response}

        app.get("/health", response_model=HealthStatus)(self.health_check)

        self.start_time = time.time()
        uvicorn.run(app, host="0.0.0.0", port=self.port)
