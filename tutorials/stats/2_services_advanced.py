# %% [markdown]
"""
# 2. Services Advanced

The following examples shows how to decorate several functions
for statistics collection.
"""


# %%
import asyncio

from dff.script import Context
from dff.pipeline import Pipeline, ACTOR, Service, ExtraHandlerRuntimeInfo, to_service
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.stats import OtelInstrumentor, set_logger_destination, set_tracer_destination
from dff.stats import OTLPLogExporter, OTLPSpanExporter
from dff.stats import default_extractors
from dff.utils.testing import is_interactive_mode

# %% [markdown]
"""
As is the case with the regular handlers, you can add extractors
both before and after the target service.
You can use a handler that runs before the service to compare the pre-service and post-service
states of the context, measure the running time, etc.

The output can be saved to and subsequently obtained from one of the following `Context` fields:
`misc` or `framework_states`. Unlike the contents of `misc`, the contents of `framework_states`
get cleared on every turn and do not get persisted to a context storage.

Pass before- and after-handlers to the respective parameters of the `to_service` decorator.

"""


# %%
set_logger_destination(OTLPLogExporter("grpc://localhost:4317", insecure=True))
set_tracer_destination(OTLPSpanExporter("grpc://localhost:4317", insecure=True))
dff_instrumentor = OtelInstrumentor()
dff_instrumentor.instrument()


@dff_instrumentor
async def get_service_state(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    # extract execution state of service from info
    data = {
        "execution_state": info.component.execution_state,
    }
    # return a record to save into connected database
    return data


# %%
# The cell demonstrates how extractor functions can be accessed for use in services.
# `get_service_state` is accessed by passing the function directly.
@to_service(
    after_handler=[
        get_service_state,
        default_extractors.get_timing_after,
        default_extractors.get_current_label,
    ],
    before_handler=[default_extractors.get_timing_before],
)
async def heavy_service(ctx: Context):
    _ = ctx  # get something from ctx if needed
    await asyncio.sleep(0.02)


# %%
pipeline = Pipeline.from_dict(
    {
        "script": TOY_SCRIPT,
        "start_label": ("greeting_flow", "start_node"),
        "fallback_label": ("greeting_flow", "fallback_node"),
        "components": [
            heavy_service,  # add `heavy_service` before the actor
            Service(
                handler=ACTOR,
                before_handler=[default_extractors.get_timing_before],
                after_handler=[
                    get_service_state,
                    default_extractors.get_timing_after,
                    default_extractors.get_current_label,
                ],
            ),
        ],
    }
)


if __name__ == "__main__":
    if is_interactive_mode():
        pipeline.run()
