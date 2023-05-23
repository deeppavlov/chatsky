# %% [markdown]
"""
# 3. Service Groups

The following examples illustrates how to obtain statistics from
several service groups.
"""


# %%
import os
import asyncio

from dff.script import Context
from dff.pipeline import Pipeline, ACTOR, ServiceGroup, ExtraHandlerRuntimeInfo
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.stats.otel import configure_logger, configure_tracer
from opentelemetry.trace import get_tracer
from opentelemetry._logs import get_logger


# %% [markdown]
"""
Handlers can be applied to any pipeline component, including service groups.
The `ServiceGroup` constructor has `before_handler` and `after_handler` parameters,
to which handler functions can be passed.

You can also collect statistics of service groups that consist of multiple services.
This can be done in the manner demonstrated below.
"""


# %%
configure_logger()
logger = get_logger(__name__)
configure_tracer()
tracer = get_tracer(__name__)


async def heavy_service(_):
    await asyncio.sleep(0.02)


async def get_group_stats(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    data = {"runtime_state": info["component"]["execution_state"]}
    return data


# %%
pipeline = Pipeline.from_dict(
    {
        "script": TOY_SCRIPT,
        "start_label": ("greeting_flow", "start_node"),
        "fallback_label": ("greeting_flow", "fallback_node"),
        "components": [
            ServiceGroup(
                before_handler=default_extractor_pool.before,
                after_handler=[get_group_stats, *default_extractor_pool.after],
                components=[{"handler": heavy_service}, {"handler": heavy_service}],
            ),
            ACTOR,
        ],
    }
)

if __name__ == "__main__":
    pipeline.run()
