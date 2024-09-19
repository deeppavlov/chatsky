# %% [markdown]
"""
# 3. Pipeline dict with services (full)

The following tutorial shows `pipeline` creation from dict
and most important pipeline components.

This tutorial is a more advanced version of the
[previous tutorial](
%doclink(tutorial,pipeline.3_pipeline_dict_with_services_basic)
).
"""

# %pip install chatsky

# %%
import json
import logging
import urllib.request

from chatsky import Context, Pipeline
from chatsky.messengers.console import CLIMessengerInterface
from chatsky.core.service import Service, ServiceRuntimeInfo
from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
)

from chatsky.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH

logger = logging.getLogger(__name__)


# %% [markdown]
"""
When Pipeline is created using Pydantic's `model_validate` method
or `Pipeline`'s constructor method, pipeline should be
defined as a dictionary of a particular structure:

* `messenger_interface` - `MessengerInterface` instance,
        is used to connect to channel and transfer IO to user.
* `context_storage` - Place to store dialog contexts
        (dictionary or a `DBContextStorage` instance).
* `pre-services` - A `ServiceGroup` object,
        basically a list of `Service` objects or more `ServiceGroup` objects,
        see tutorial 4.
* `post-services` - A `ServiceGroup` object,
        basically a list of `Service` objects or more `ServiceGroup` objects,
        see tutorial 4.
* `before_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See tutorials 6 and 7.
* `after_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See tutorials 6 and 7.
* `timeout` - Pipeline timeout, see tutorial 5.
* `optimization_warnings` - Whether pipeline asynchronous structure
        should be checked during initialization,
        see tutorial 5.

On pipeline execution services from
`components` = 'pre-services' + actor + 'post-services'
list are run without difference between pre- and postprocessors.
`Service` object can be defined either with callable
(see tutorial 2) or with dict of structure / `Service` object
 with following constructor arguments:


* `handler` (required) - ServiceFunction.
* `before_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See tutorials 6 and 7.
* `after_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See tutorials 6 and 7.
* `timeout` - service timeout, see tutorial 5.
* `asynchronous` - whether or not this service _should_ be asynchronous
        (keep in mind that not all services _can_ be asynchronous),
        see tutorial 5.
* `start_condition` - service start condition, see tutorial 4.
* `name` - custom defined name for the service
        (keep in mind that names in one ServiceGroup should be unique),
        see tutorial 4.

Not only Pipeline can be run using `__call__` method,
for most cases `run` method should be used.
It starts pipeline asynchronously and connects to provided messenger interface.

Here pipeline contains 3 services,
defined in 3 different ways with different signatures.
First two of them write sample feature detection data to `ctx.misc`.
The first uses a constant expression and the second fetches from `example.com`.
Final service logs `ctx.misc` dict.
"""


# %%
def prepreprocess(ctx: Context):
    logger.info(
        "preprocession intent-detection Service running (defined as a dict)"
    )
    ctx.misc["preprocess_detection"] = {
        ctx.last_request.text: "some_intent"
    }  # Similar syntax can be used to access
    # service output dedicated to current pipeline run


def preprocess(ctx: Context, _, info: ServiceRuntimeInfo):
    logger.info(
        f"another preprocession web-based annotator Service"
        f"(defined as a callable), named '{info.name}'"
    )
    with urllib.request.urlopen("https://example.com/") as webpage:
        web_content = webpage.read().decode(
            webpage.headers.get_content_charset()
        )
        ctx.misc["another_detection"] = {
            ctx.last_request.text: (
                "online" if "Example Domain" in web_content else "offline"
            )
        }


def postprocess(ctx: Context, pl: Pipeline):
    logger.info("postprocession Service (defined as an object)")
    logger.info(
        f"resulting misc looks like:"
        f"{json.dumps(ctx.misc, indent=4, default=str)}"
    )
    received_response = pl.script.get_inherited_node(pl.fallback_label).response
    responses_match = received_response == ctx.last_response
    logger.info(f"actor is{'' if responses_match else ' not'} in fallback node")


# %%
pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "messenger_interface": CLIMessengerInterface(
        intro="Hi, this is a brand new Pipeline running!",
        prompt_request="Request: ",
        prompt_response="Response: ",
    ),  # `CLIMessengerInterface` has the following constructor parameters:
    #     `intro` - a string that will be displayed
    #           on connection to interface (on `pipeline.run`)
    #     `prompt_request` - a string that will be displayed before user input
    #     `prompt_response` - an output prefix string
    "context_storage": {},
    "pre_services": [
        {
            "handler": prepreprocess,
            "name": "preprocessor",
        },
        preprocess,
    ],
    "post_services": Service(handler=postprocess, name="postprocessor"),
}


# %%
pipeline = Pipeline.model_validate(pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH, printout=True)
    if is_interactive_mode():
        pipeline.run()
