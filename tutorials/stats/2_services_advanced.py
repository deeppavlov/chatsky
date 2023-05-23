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
from dff.stats.utils import set_logger_destination, set_tracer_destination
from dff.stats.instrumentor import DFFInstrumentor
from dff.stats import defaults

# %% [markdown]
"""
As is the case with the regular handlers, you can add extractors
both before and after the target service.
You can use a handler that runs before the service to compare the pre-service and post-service
states of the context, measure the running time, etc.
An example of such handler can be found in the default extractor pool.

Pass before- and after-handlers to the respective parameters of the `to_service` decorator.

As for using multiple pools, you can subscribe your storage to any number of pools.

"""


# %%
set_logger_destination("grpc://localhost:4317")
set_tracer_destination("grpc://localhost:4317")
dff_instrumentor = DFFInstrumentor()


@dff_instrumentor
async def get_service_state(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    # extract execution state of service from info
    data = {
        "execution_state": info["component"]["execution_state"],
    }
    # return a record to save into connected database
    return data


# %%
# The cell demonstrates how extractor functions can be accessed for use in services.
# `get_service_state` is accessed by passing the function directly.
# Lists of extractors from `before` and `after` groups are accessed as pool attributes.
@to_service(
    after_handler=[
        get_service_state,
        defaults.get_timing_after,
        defaults.get_current_label,
    ],
    before_handler=[defaults.get_timing_before],
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
            Service(handler=heavy_service),  # add `heavy_service` before the actor
            Service(
                handler=to_service(
                    before_handler=[defaults.get_timing_before],
                    after_handler=[
                        get_service_state,
                        defaults.get_timing_after,
                        defaults.get_current_label,
                    ],
                )(
                    ACTOR
                )  # wrap and add the actor
            ),
        ],
    }
)


if __name__ == "__main__":
    pipeline.run()
