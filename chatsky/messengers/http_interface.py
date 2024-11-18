import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import dotenv
from chatsky.messengers.common import MessengerInterface
from chatsky.core import Message
import os

dotenv.load_dotenv()

HTTP_INTERFACE_PORT = int(os.getenv("PORT", 8020))


class HTTPMessengerInterface(MessengerInterface):
    async def connect(self, pipeline_runner):
        app = FastAPI()

        class Output(BaseModel):
            user_id: str
            response: Message

        @app.post("/chat", response_model=Output)
        async def respond(
            user_id: str,
            user_message: str,  # TODO: change type to Message after core rework is done
        ):
            message = Message(text=user_message)
            context = await pipeline_runner(message)
            return {"user_id": user_id, "response": context.last_response}

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=HTTP_INTERFACE_PORT,
        )
