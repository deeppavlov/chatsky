# %% [markdown]
"""
# 4. Global Services

The following example demonstrates how to collect statistics
from several global services.
"""


# %%
import asyncio

from dff.script import Context
from dff.pipeline import Pipeline, ACTOR, ExtraHandlerRuntimeInfo, GlobalExtraHandlerType
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH
from dff.stats import OtelInstrumentor, set_logger_destination, set_tracer_destination
from dff.stats import OTLPLogExporter, OTLPSpanExporter
from dff.stats import default_extractors
from dff.utils.testing import is_interactive_mode, check_happy_path


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
set_logger_destination(OTLPLogExporter("grpc://localhost:4317", insecure=True))
set_tracer_destination(OTLPSpanExporter("grpc://localhost:4317", insecure=True))
dff_instrumentor = OtelInstrumentor()
dff_instrumentor.instrument()


@dff_instrumentor
async def get_pipeline_state(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    data = {"execution_state": info.component.execution_state}
    return data


async def heavy_service(_):
    await asyncio.sleep(0.02)


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
pipeline.add_global_handler(GlobalExtraHandlerType.BEFORE_ALL, default_extractors.get_timing_before)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, default_extractors.get_timing_after)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, get_pipeline_state)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        pipeline.run()
