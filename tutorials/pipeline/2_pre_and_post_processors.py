# %% [markdown]
"""
# 2. Pre- and postprocessors

The following tutorial shows more advanced usage of `pipeline`
module as an extension to `chatsky.script.core`.

Here, %mddoclink(api,core.context,Context.misc)
dictionary of context is used for storing additional data.
"""

# %pip install chatsky

# %%
import logging
import sys
from importlib import reload

from chatsky.messengers.console import CLIMessengerInterface
from chatsky import Context, Pipeline

from chatsky.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    HAPPY_PATH,
    TOY_SCRIPT_KWARGS,
)

reload(logging)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="")
logger = logging.getLogger(__name__)


# %% [markdown]
"""
When Pipeline is created, additional pre-
and post-services can be defined.
These can be any callables, certain objects or dicts.
They are being turned into special `Service` or `ServiceGroup` objects
(see %mddoclink(tutorials.pipeline.3_pipeline_dict_with_services_full)),
that will be run before or after `Actor` respectively.
These services can be used to access external APIs, annotate user input, etc.

Service callables only take one parameter: `ctx`,
where `ctx` is the `Context` object of the current dialog.
(see %mddoclink(tutorials.pipeline.3_pipeline_dict_with_services_full))

Here a preprocessor ("ping") and a postprocessor ("pong") are added to pipeline.
They share data in `context.misc` -
a common place for sharing data between services and actor.
"""


# %%
def ping_processor(ctx: Context):
    logger.info("ping - ...")
    ctx.misc["ping"] = True


def pong_processor(ctx: Context):
    ping_pong = ctx.misc.get("ping", False)
    logger.info("... - pong")
    logger.info(
        f"Ping-pong exchange: " f"{'completed' if ping_pong else 'failed'}."
    )


# %%
pipeline = Pipeline(
    **TOY_SCRIPT_KWARGS,
    context_storage={},  # `context_storage` - a dictionary or
    # a `DBContextStorage` instance,
    # a place to store dialog contexts
    messenger_interface=CLIMessengerInterface(),
    # `messenger_interface` - a message channel adapter,
    # it's not used in this tutorial
    pre_services=[ping_processor],
    post_services=[pong_processor],
)


if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH, printout=True)
    if is_interactive_mode():
        pipeline.run()
