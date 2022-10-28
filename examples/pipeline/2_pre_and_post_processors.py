"""
Pre- and postprocessors
=======================

The following example shows more advanced usage of `pipeline` module, as an extension to `dff.core.engine`
"""

import logging

from dff.core.engine.core import Context

from dff.core.pipeline import Pipeline, CLIMessengerInterface
from examples.pipeline._pipeline_utils import SCRIPT, get_auto_arg, auto_run_pipeline

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

"""
When Pipeline is created with `from_script` method, additional pre- and postprocessors can be defined.
These can be any ServiceBuilder objects (defined in `types` module) - callables, objects or dicts.
They are being turned into special Service objects (see example №3),
that will be run before or after Actor respectively.
These services can be used to access external APIs, annotate user input, etc.

Service callable signature can be one of the following: [ctx], [ctx, actor] or [ctx, actor, info] (see example №3),
where:
    `ctx` - Context of the current dialog
    `actor` - Actor of the pipeline
    `info` - dictionary, containing information about current service and pipeline execution state (see example №4)

Here a preprocessor ("ping") and a postprocessor ("pong") are added to pipeline.
They share data in `context.misc` - a common place for sharing data between services and actor.
"""


def ping_processor(ctx: Context):
    ctx.misc["ping"] = True


def pong_processor(ctx: Context):
    ping = ctx.misc.get("ping", False)
    ctx.misc["pong"] = ping


pipeline = Pipeline.from_script(
    SCRIPT,
    ("greeting_flow", "start_node"),
    ("greeting_flow", "fallback_node"),
    {},  # `context_storage` - a dictionary or a `DBAbstractConnector` instance, a place to store dialog contexts
    CLIMessengerInterface(),  # `messenger_interface` - a message channel adapter, it's not used in this example
    [ping_processor],
    [pong_processor],
)


if __name__ == "__main__":
    if get_auto_arg():
        auto_run_pipeline(pipeline, logger=logger)
    else:
        ctx_id = 0  # 0 will be current dialog (context) identification.
        while True:
            ctx: Context = pipeline(input("Send request: "), ctx_id)
            print(f"Response: {ctx.last_response}")
            ping_pong = ctx.misc.get("ping", False) and ctx.misc.get("pong", False)
            print(f"Ping-pong exchange: {'completed' if ping_pong else 'failed'}.")
            logger.info(f"Context misc: {ctx.misc}")
