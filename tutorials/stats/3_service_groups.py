# %% [markdown]
"""
# 3. Service Groups

The following examples illustrates how to obtain statistics from
several service groups.
"""


# %%
import asyncio

from dff.script import Context
from dff.pipeline import Pipeline, ACTOR, ServiceGroup, ExtraHandlerRuntimeInfo
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.stats import DFFInstrumentor, set_logger_destination, set_tracer_destination
from dff.stats import OTLPLogExporter, OTLPSpanExporter
from dff.stats import defaults


# %% [markdown]
"""
Handlers can be applied to any pipeline component, including service groups.
The `ServiceGroup` constructor has `before_handler` and `after_handler` parameters,
to which handler functions can be passed.

You can also collect statistics of service groups that consist of multiple services.
This can be done in the manner demonstrated below.
"""


# %%
dff_instrumentor = DFFInstrumentor()


async def heavy_service(_):
    await asyncio.sleep(0.02)


@dff_instrumentor
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
                before_handler=[defaults.get_timing_before],
                after_handler=[
                    get_group_stats,
                    defaults.get_timing_after,
                    defaults.get_current_label,
                ],
                components=[{"handler": heavy_service}, {"handler": heavy_service}],
            ),
            ACTOR,
        ],
    }
)

if __name__ == "__main__":
    set_logger_destination(OTLPLogExporter("grpc://localhost:4317"))
    set_tracer_destination(OTLPSpanExporter("grpc://localhost:4317"))
    dff_instrumentor.instrument()
    pipeline.run()
