# %% [markdown]
"""
# Web API: 1. FastAPI

This tutorial shows how to create an API for DFF using FastAPI.

You can see the result at http://127.0.0.1:8000/docs.

Here, `_run_pipeline` (same as %mddoclink(api,pipeline.pipeline.pipeline,Pipeline.run))
method is used to execute pipeline once.

%mddoclink(api,script.core.message,Message) is used in creating a JSON Schema for the endpoint.
"""

# %pip install dff uvicorn fastapi

# %%
from dff.script import Message
from dff.pipeline import Pipeline
from dff.utils.testing import TOY_SCRIPT_ARGS, is_interactive_mode

import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI


# %%
pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS)


# %%
app = FastAPI()


class Output(BaseModel):
    user_id: str
    response: Message


@app.post("/chat", response_model=Output)
async def respond(
    user_id: str,
    user_message: Message,
):
    context = await pipeline._run_pipeline(
        user_message, user_id
    )  # run in async
    return {"user_id": user_id, "response": context.last_response}


# %%
if __name__ == "__main__":
    if is_interactive_mode():  # do not run this during doc building
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
        )
