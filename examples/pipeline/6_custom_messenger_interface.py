"""
Custom messenger interface
==========================

The following example shows messenger interfaces usage
"""

import logging

from dff.core.engine.core import Context, Actor
from dff.core.engine.core.context import get_last_index
from flask import Flask, request, Request

from dff.core.pipeline import Pipeline, CallbackMessengerInterface
from dff._example_utils.index import SCRIPT, is_in_notebook

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

"""
Messenger interfaces are used for providing a way for communication between user and pipeline.
They manage message channel initialization and termination as well as pipeline execution on every user request.
There are two built-in messenger interface types (that may be overridden):
    `PollingMessengerInterface` - starts polling for user request in a loop upon initialization,
                                  it has following methods:
        `_request()` - method that is executed in a loop, should return list of tuples: (user request, unique dialog id)
        `_respond(responses)` - method that is executed in a loop after all user requests processing,
                                accepts list of dialog Contexts
        `_on_exception(e)` - method that is called on exception that happens in the loop,
                             should catch the exception (it is also called on pipeline termination)
        `connect(pipeline_runner, loop, timeout)` - method that is called on connection to message channel,
                                                    accepts pipeline_runner (a callback, running pipeline)
            loop - a function to be called on each loop execution (should return True to continue polling)
            timeout - time in seconds to wait between loop executions
    `CallbackMessengerInterface` - creates message channel and provides a callback for pipeline execution,
                                   it has following methods:
        `on_request(request, ctx_id)` - method that should be called each time user provides new input to pipeline,
                                        returns dialog Context
`CLIMessengerInterface` is also a messenger interface that overrides `PollingMessengerInterface` and
    provides default message channel between pipeline and console/file IO

Here a default `CallbackMessengerInterface` is used to setup communication between pipeline and Flask server.
Two services are used to process request:
    `purify_request` extracts user request from Flask HTTP request
    `construct_webpage_by_response` wraps actor response in webpage and adds response-based image to it
"""

app = Flask("examples.6_custom_messenger_interface")

actor = Actor(SCRIPT, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))

messenger_interface = (
    CallbackMessengerInterface()
)  # For this simple case of Flask, CallbackMessengerInterface may not be overridden


def construct_webpage_by_response(response: str, _: Context) -> str:
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
        <img src="https://source.unsplash.com/random?{response}" alt="Response picture" style="width:50%;height:50%;">
        </body>
    </html>
    """


def purify_request(ctx: Context):
    last_request = ctx.last_request  # TODO: add _really_ nice ways to modify user request and response
    last_index = get_last_index(ctx.requests)
    if isinstance(last_request, Request):
        logger.info(f"Capturing request from: {last_request.base_url}")
        ctx.requests[last_index] = last_request.args.get("request")
    elif isinstance(last_request, str):
        logger.info("Capturing request from CLI")
        ctx.requests[last_index] = last_request
    else:
        raise Exception(f"Request of type {type(last_request)} can not be purified!")


def markdown_request(ctx: Context):
    last_response = ctx.last_response
    last_index = get_last_index(ctx.responses)
    ctx.responses[last_index] = construct_webpage_by_response(last_response, ctx)


pipeline_dict = {
    "messenger_interface": messenger_interface,
    "components": [
        purify_request,
        {
            "handler": actor,
            "name": "encapsulated-actor",
        },  # Actor here is encapsulated in another service with specific name
        markdown_request,
    ],
}


@app.route("/pipeline_web_interface")
async def route():
    ctx_id = 0  # 0 will be current dialog (context) identification.
    return messenger_interface.on_request(request, ctx_id).last_response


pipeline = Pipeline(**pipeline_dict)

if __name__ == "__main__" and not is_in_notebook():
    pipeline.run()
    app.run()
    # Navigate to http://127.0.0.1:5000/pipeline_web_interface?request={REQUEST} to receive response
    # e.g. http://127.0.0.1:5000/pipeline_web_interface?request=Hi will bring you to actor start node
