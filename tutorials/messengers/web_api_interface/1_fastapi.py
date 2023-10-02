# %% [markdown]
"""
# Web API: 2. FastAPI

This tutorial shows how to create an API for DFF using FastAPI.

You can see the result at http://127.0.0.1:8000/docs.
"""

# %pip install dff uvicorn fastapi

# %%
from dff.messengers.common.interface import CallbackMessengerInterface
from dff.script import Message
from dff.pipeline import Pipeline
from dff.utils.testing import TOY_SCRIPT_ARGS, is_interactive_mode

import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI

# %% [markdown]
"""
Messenger interfaces establish communication between users and the pipeline.
They manage message channel initialization and termination
as well as pipeline execution on every user request.
There are two built-in messenger interface types (that may be overridden):

* `PollingMessengerInterface` - Starts polling for user requests
    in a loop upon initialization,
    it has following methods:
    
    * `_request()` - Method that is executed in a loop,
        should return list of tuples: (user request, unique dialog id).
    * `_respond(responses)` - Method that is executed in a loop
        after all user requests processing,
        accepts list of dialog `Contexts`.
    * `_on_exception(e)` - Method that is called on
        exception that happens in the loop,
        should catch the exception
        (it is also called on pipeline termination).
    * `connect(pipeline_runner, loop, timeout)` -
        Method that is called on connection to message channel,
        accepts pipeline_runner (a callback, running pipeline).
    * loop - A function to be called on each loop
        execution (should return True to continue polling).
    * timeout - Time in seconds to wait between loop executions.

* `CallbackMessengerInterface` - Creates message channel
    and provides a callback for pipeline execution,
    it has following method:
    
    * `on_request(request, ctx_id)` - Method that should be called each time
        user provides new input to pipeline,
        returns dialog Context.

`CLIMessengerInterface` is also
a messenger interface that overrides `PollingMessengerInterface` and
provides default message channel between pipeline and console/file IO.

Here the default `CallbackMessengerInterface` is used to setup
communication between the pipeline on the server side and the messenger client.
"""

# %%
messenger_interface = CallbackMessengerInterface()
# CallbackMessengerInterface instantiating the dedicated messenger interface
pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, messenger_interface=messenger_interface)


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
    context = messenger_interface.on_request(user_message, user_id)
    return {"user_id": user_id, "response": context.last_response}


# %%
if __name__ == "__main__":
    if is_interactive_mode():  # do not run this during doc building
        pipeline.run()
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
        )
