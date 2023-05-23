# %% [markdown]
"""
# 4. Global Services

The following example demonstrates how to collect statistics
from several global services.
"""


# %%
import os
import asyncio

from dff.script import Context
from dff.pipeline import Pipeline, ACTOR, ExtraHandlerRuntimeInfo, GlobalExtraHandlerType
from dff.stats.defaults import extract_timing_before, extract_timing_after
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.stats.otel import configure_logger, configure_tracer
from opentelemetry.trace import get_tracer
from opentelemetry._logs import get_logger


# %% [markdown]
"""
As in case with regular handlers, you can define global statistic handlers
that will be applied to every element inside the pipeline.

Use the `add_global_handler` method provided by the `Pipeline` class.

Like any global handler, handlers for statistics collection can be wired
to run at any stage of `Pipeline` execution. In the following examples,
we add handlers before and after all the services
in order to measure the exact running time of the pipeline.
"""


# %%
configure_logger()
logger = get_logger(__name__)
configure_tracer()
tracer = get_tracer(__name__)


async def heavy_service(_):
    await asyncio.sleep(0.02)


async def get_pipeline_state(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    data = {"runtime_state": info["component"]["execution_state"]}
    return data


# %%
pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "components": [
        [heavy_service for _ in range(0, 5)],
        ACTOR,
    ],
}
pipeline = Pipeline.from_dict(pipeline_dict)
pipeline.add_global_handler(GlobalExtraHandlerType.BEFORE_ALL, extract_timing_before)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, extract_timing_after)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, get_pipeline_state)

if __name__ == "__main__":
    pipeline.run()
