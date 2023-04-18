# %% [markdown]
"""
# 9. JSON storage with web API

This is a tutorial on using JSON with FastAPI.
"""


# %%
import pathlib

from dff.context_storages import context_storage_factory
from dff.script import Message
from dff.pipeline import Pipeline
from dff.utils.testing.common import check_happy_path, is_interactive_mode
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH

import uvicorn

from fastapi import FastAPI

# %%
app = FastAPI()

pathlib.Path("dbs").mkdir(exist_ok=True)
db = context_storage_factory("json://dbs/file.json")


@app.post("/chat")
async def respond(user_id: int,
                  user_message: str,
                  ):
    request = Message(text=user_message)
    context = pipeline(request, user_id)
    return {"user_id": user_id,
            "response": context.last_response}


# %%
pipeline = Pipeline.from_script(
    TOY_SCRIPT,
    context_storage=db,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)


# %%
if __name__ == "__main__":
    # check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        uvicorn.run(
            app,
            host='127.0.0.1',
            port=8000,
        )  # This runs tutorial in interactive mode (via FastAPI, as a web server)
