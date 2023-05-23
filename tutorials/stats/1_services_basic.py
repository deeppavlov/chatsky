# %% [markdown]
"""
# 1. Services Basic

The following examples shows the basics of using the `stats` module.
Assuming that your pipeline includes various services, you can decorate
these functions to collect statistics and persist them to a database.
"""


# %%
import asyncio

from dff.script import Context
from dff.pipeline import Pipeline, ACTOR, Service, ExtraHandlerRuntimeInfo, to_service
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.stats import DFFInstrumentor, set_logger_destination, set_tracer_destination


# %% [markdown]
"""
The statistics are collected from services by wrapping them in special 'extractor' functions.
These functions have a specific signature: their arguments are always a `Context`, an `Pipeline`,
and an `ExtraHandlerRuntimeInfo`. Their return value is always a `StatsRecord` instance.
It is a preferred practice to define them as asynchronous functions.

Before you use the said functions, you should create an `StatsExtractorPool`
or import a ready one as a first step.

Then, you should define the handlers and add them to some pool,
using either `add_extractor` (see below).

Finally, one should also create a `StatsStorage`, which compresses data into batches
and saves it to a database. The database credentials can be configured by either
instantiating a `Saver` class and passing it on construction, or by
passing the database credentials to the `from_uri` class method.

When this is done, subscribe the storage to one or more pools that you have created
by calling the `add_subscriber` method.

The whole process is illustrated in the example below.

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
# set get_service_state to run it after the `heavy_service`
@to_service(after_handler=[get_service_state])
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
            Service(handler=heavy_service),
            Service(handler=to_service(after_handler=[get_service_state])(ACTOR)),
        ],
    }
)


if __name__ == "__main__":
    pipeline.run()
