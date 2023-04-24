# %% [markdown]
"""
# Web API: 1. FastAPI

This tutorial shows how to create an API for DFF using FastAPI.

You can see the result at http://127.0.0.1:8000/docs.
"""


# %%
from dff.script import Message
from dff.pipeline import Pipeline
from dff.utils.testing import TOY_SCRIPT, is_interactive_mode

import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI


# %%
pipeline = Pipeline.from_script(
    TOY_SCRIPT, ("greeting_flow", "start_node"), ("greeting_flow", "fallback_node")
)


# %%
app = FastAPI()


class Output(BaseModel):
    user_id: int
    response: Message


@app.post("/chat", response_model=Output)
async def respond(
    user_id: int,
    user_message: str,
):
    request = Message(text=user_message)
    context = await pipeline._run_pipeline(request, user_id)  # run in async
    return {"user_id": user_id, "response": context.last_response}


# %%
if __name__ == "__main__":
    if is_interactive_mode():  # do not run this during doc building
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
        )
