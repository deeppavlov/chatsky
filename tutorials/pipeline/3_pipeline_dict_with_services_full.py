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
import urllib.request
import logging
import sys
from importlib import reload

from chatsky import Context, Pipeline
from chatsky.messengers.console import CLIMessengerInterface
from chatsky.core.service import Service
from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
)

from chatsky.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH

reload(logging)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="")
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
        see [tutorial 4](
        %doclink(tutorial,pipeline.4_groups_and_conditions_basic)).
* `post-services` - A `ServiceGroup` object,
        basically a list of `Service` objects or more `ServiceGroup` objects,
        see [tutorial 4](
        %doclink(tutorial,pipeline.4_groups_and_conditions_basic)).
* `before_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See [tutorial 6]%doclink(tutorial,pipeline.6_extra_handlers_basic)
        and [tutorial 7](
        %doclink(tutorial,pipeline.7_extra_handlers_and_extensions)).
* `after_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See [tutorial 6]%doclink(tutorial,pipeline.6_extra_handlers_basic)
        and [tutorial 7](
        %doclink(tutorial,pipeline.7_extra_handlers_and_extensions)).
* `timeout` - Pipeline timeout, see [tutorial 5](
        %doclink(tutorial,pipeline.5_asynchronous_groups_and_services)).

On pipeline execution services from
`components` = 'pre-services' + actor + 'post-services'
list are run without difference between pre- and postprocessors.
`Service` object can be defined either with callable
(see [tutorial 2]%doclink(tutorial,pipeline.7_extra_handlers_and_extensions)).
or with dict of structure / `Service` object
with following constructor arguments:


* `handler` (required) - ServiceFunction.
* `before_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See [tutorial 6]%doclink(tutorial,pipeline.6_extra_handlers_basic)
        and [tutorial 7](
        %doclink(tutorial,pipeline.7_extra_handlers_and_extensions)).
* `after_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See [tutorial 6]%doclink(tutorial,pipeline.6_extra_handlers_basic)
        and [tutorial 7](
        %doclink(tutorial,pipeline.7_extra_handlers_and_extensions)).
* `timeout` - service timeout, see [tutorial 5](
        %doclink(tutorial,pipeline.5_asynchronous_groups_and_services)).
* `asynchronous` - whether or not this service _should_ be asynchronous
        (keep in mind that not all services _can_ be asynchronous),
        see [tutorial 5](
        %doclink(tutorial,pipeline.5_asynchronous_groups_and_services)).
* `start_condition` - service start condition, see [tutorial 4](
        %doclink(tutorial,pipeline.4_groups_and_conditions_basic)).
* `name` - custom defined name for the service
        (keep in mind that names in one ServiceGroup should be unique),
        see [tutorial 4](
        %doclink(tutorial,pipeline.4_groups_and_conditions_basic)).

Services can also be defined as a child class of `Service`, so that
you can get access to the `self` object to get more
information about your `Service` and log it.
To do that you need to derive your class from `Service`,
then add an async `call()` method which now will be called
instead of the `handler`. (see the `PreProcess` example below)
You don't need to worry about the `handler` field, it can be empty.

Please note that if you are defining a Service this way,
`handler` won't run automatically. So, you could add a line
like "await self.handler(ctx)" or "self.handler(ctx)" directly to your
`call()` method, depending on what your `handler` is.

Not only Pipeline can be run using `__call__` method,
for most cases `run` method should be used.
It starts pipeline asynchronously and connects to provided messenger interface.

Here pipeline contains 3 services, used in 3 different ways.
First two of them write sample feature detection data to `ctx.misc`.
The first uses a constant expression and is defined as a Service function,
while the second fetches from `example.com` and derives a class from Service.
Final service logs `ctx.misc` dict, using access to the pipeline
from `ctx.pipeline`.
"""


# %%
async def prepreprocess(ctx: Context):
    logger.info(
        "preprocession intent-detection Service running (defined as a dict)"
    )
    ctx.misc["preprocess_detection"] = {
        ctx.last_request.text: "some_intent"
    }  # Similar syntax can be used to access
    # service output dedicated to current pipeline run


class PreProcess(Service):
    async def call(self, ctx: Context):
        logger.info(
            f"another preprocession web-based annotator Service"
            f"(defined as a callable), named '{self.name}'"
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


async def postprocess(ctx: Context):
    logger.info("postprocession Service (defined as an object)")
    logger.info(
        f"resulting misc looks like:"
        f"{json.dumps(ctx.misc, indent=4, default=str)}"
    )
    pl = ctx.pipeline
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
        PreProcess(),
    ],
    "post_services": Service(handler=postprocess, name="postprocessor"),
}

# %%
pipeline = Pipeline.model_validate(pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH, printout=True)
    if is_interactive_mode():
        pipeline.run()
