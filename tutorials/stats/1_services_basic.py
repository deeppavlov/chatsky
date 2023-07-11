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
from dff.stats import OtelInstrumentor, set_logger_destination, set_tracer_destination
from dff.stats import OTLPLogExporter, OTLPSpanExporter


# %% [markdown]
"""
The statistics are collected from services by adding `extractor` functions as extra handlers.
These functions have a specific signature: the expected arguments are always `Context`, `Pipeline`,
and `ExtraHandlerRuntimeInfo`. The expected return value is an arbitrary `dict`.
It is a preferred practice to define them as asynchronous functions.

The initial step in instrumenting a DFF application using Opentelemetry is to configure the
export destination. To achieve this, you can use the functions provided by the `stats` module:
`set_logger_destination`, `set_tracer_destination`, or `set_meter_destination`. These accept
an appropriate Opentelemetry exporter instance and bind it to provider classes.

Nextly, the `OtelInstrumentor` class should be constructed that logs the output of extractors.
Custom extractors can be decorated with the `OtelInstrumentor` instance.
Default extractors are instrumented by calling the `instrument` method on the `OtelInstrumentor`.

The whole process is illustrated in the example below.

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
            heavy_service,
            Service(handler=ACTOR, after_handler=[get_service_state]),
        ],
    }
)


if __name__ == "__main__":
    pipeline.run()
