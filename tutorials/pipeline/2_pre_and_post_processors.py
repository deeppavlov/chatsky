# %% [markdown]
"""
# 2. Pre- and postprocessors

The following tutorial shows more advanced usage of `pipeline`
module as an extension to `chatsky.script.core`.

Here, %mddoclink(api,script.core.context,Context.misc)
dictionary of context is used for storing additional data.
"""

# %pip install chatsky

# %%
import logging

from chatsky.messengers.console import CLIMessengerInterface
from chatsky.script import Context, Message

from chatsky.pipeline import Pipeline

from chatsky.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    HAPPY_PATH,
    TOY_SCRIPT_KWARGS,
)

logger = logging.getLogger(__name__)


# %% [markdown]
"""
When Pipeline is created, additional pre-
and post-services can be defined.
These can be any callables, certain objects or dicts.
They are being turned into special `Service` or `ServiceGroup` objects
(see tutorial 3),
that will be run before or after `Actor` respectively.
These services can be used to access external APIs, annotate user input, etc.

Service callable signature can be one of the following:
`[ctx]`, `[ctx, pipeline]` or `[ctx, actor, info]` (see tutorial 3),
where:

* `ctx` - Context of the current dialog.
* `pipeline` - The current pipeline.
* `info` - dictionary, containing information about
        current service and pipeline execution state (see tutorial 4).

Here a preprocessor ("ping") and a postprocessor ("pong") are added to pipeline.
They share data in `context.misc` -
a common place for sharing data between services and actor.
"""


# %%
def ping_processor(ctx: Context):
    ctx.misc["ping"] = True


def pong_processor(ctx: Context):
    ping = ctx.misc.get("ping", False)
    ctx.misc["pong"] = ping


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
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        ctx_id = 0  # 0 will be current dialog (context) identification.
        while True:
            message = Message(input("Send request: "))
            ctx: Context = pipeline(message, ctx_id)
            print(f"Response: {ctx.last_response}")
            ping_pong = ctx.misc.get("ping", False) and ctx.misc.get(
                "pong", False
            )
            print(
                f"Ping-pong exchange: {'completed' if ping_pong else 'failed'}."
            )
            logger.info(f"Context misc: {ctx.misc}")
