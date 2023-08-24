# %% [markdown]
"""
# 6. Custom messenger interface

The following tutorial shows messenger interfaces usage.
"""

# %pip install dff flask

# %%
import logging

from dff.messengers.common.interface import CallbackMessengerInterface
from dff.script import Context, Message
from flask import Flask, request, Request

from dff.pipeline import Pipeline, ACTOR
from dff.utils.testing import is_interactive_mode, TOY_SCRIPT

logger = logging.getLogger(__name__)


# %% [markdown]
"""
Messenger interfaces are used for providing
a way for communication between user and `pipeline`.
They manage message channel initialization and termination
as well as pipeline execution on every user request.
There are two built-in messenger interface types (that may be overridden):

* `PollingMessengerInterface` - Starts polling for user request
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

Here a default `CallbackMessengerInterface` is used to setup
communication between pipeline and Flask server.
Two services are used to process request:

* `purify_request` - Extracts user request from Flask HTTP request.
* `construct_webpage_by_response` - Wraps actor response in webpage and
    adds response-based image to it.
"""

# %%
app = Flask(__name__)

messenger_interface = CallbackMessengerInterface()  # For this simple case of Flask,
# CallbackMessengerInterface may not be overridden


def construct_webpage_by_response(response: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                p {{text-align: center;}}
                img {{
                    display: block;
                    margin-left: auto;
                    margin-right: auto;
                }}
            </style>
        </head>
        <body>
        <p><b>{response}</b></p>
        <img
            src="https://source.unsplash.com/random?{response}"
            alt="Response picture" style="width:50%;height:50%;"
        >
        </body>
    </html>
    """


def purify_request(ctx: Context):
    last_request = ctx.last_request
    if isinstance(last_request, Request):
        logger.info(f"Capturing request from: {last_request.base_url}")
        ctx.last_request = Message(text=last_request.args.get("request"))
    elif isinstance(last_request, Message):
        logger.info("Capturing request from CLI")
    else:
        raise Exception(f"Request of type {type(last_request)} can not be purified!")


def cat_response2webpage(ctx: Context):
    ctx.last_response = Message(
        misc={"webpage": construct_webpage_by_response(ctx.last_response.text)}
    )


# %%
pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "messenger_interface": messenger_interface,
    "components": [
        purify_request,
        {
            "handler": ACTOR,
            "name": "encapsulated-actor",
        },  # Actor here is encapsulated in another service with specific name
        cat_response2webpage,
    ],
}


@app.route("/pipeline_web_interface")
async def route():
    ctx_id = 0  # 0 will be current dialog (context) identification.
    return messenger_interface.on_request(request, ctx_id).last_response.text


# %%
pipeline = Pipeline(**pipeline_dict)

if (
    __name__ == "__main__" and is_interactive_mode()
):  # This tutorial will be run in interactive mode only
    pipeline.run()
    app.run()
    # Navigate to
    # http://127.0.0.1:5000/pipeline_web_interface?request={REQUEST}
    # to receive response
    # e.g. http://127.0.0.1:5000/pipeline_web_interface?request=Hi
    # will bring you to actor start node
