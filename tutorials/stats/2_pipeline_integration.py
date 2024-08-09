# %% [markdown]
"""
# 2. Pipeline Integration

In the Chatsky ecosystem, extractor functions act as regular extra handlers (
[see the pipeline module documentation](
%doclink(tutorial,pipeline.6_extra_handlers_basic)
)
).
Hence, you can decorate any part of your pipeline, including services,
service groups and the pipeline as a whole, to obtain the statistics
specific for that component. Some examples of this functionality
are showcased in this tutorial.

<div class="alert alert-info">

Both the Opentelemetry collector and the Clickhouse instance must be running
during statistics collection.
If you cloned the Chatsky repo, launch them using `docker compose`:
```bash
docker compose --profile stats up
```

</div>
"""

# %pip install chatsky[stats]

# %%
import asyncio

from chatsky.pipeline import (
    Pipeline,
    ExtraHandlerRuntimeInfo,
    ServiceGroup,
    GlobalExtraHandlerType,
)
from chatsky.script import Context
from chatsky.stats import OTLPLogExporter, OTLPSpanExporter
from chatsky.stats import (
    OtelInstrumentor,
    set_logger_destination,
    set_tracer_destination,
)
from chatsky.stats import default_extractors
from chatsky.utils.testing import is_interactive_mode, check_happy_path
from chatsky.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH

# %%
set_logger_destination(OTLPLogExporter("grpc://localhost:4317", insecure=True))
set_tracer_destination(OTLPSpanExporter("grpc://localhost:4317", insecure=True))
chatsky_instrumentor = OtelInstrumentor()
chatsky_instrumentor.instrument()


# example extractor function
@chatsky_instrumentor
async def get_service_state(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    # extract execution state of service from info
    data = {
        "execution_state": info.component.execution_state,
    }
    # return a record to save into connected database
    return data


# %%
# example service
async def heavy_service(ctx: Context):
    _ = ctx  # get something from ctx if needed
    await asyncio.sleep(0.02)


# %% [markdown]
"""

The many ways in which you can use extractor functions are shown in
the following pipeline definition. The functions are used to obtain
statistics from respective components:

* A service group of two `heavy_service` instances.
* An `Actor` service.
* The pipeline as a whole.

As is the case with the regular extra handler functions,
you can wire the extractors to run either before or after the target service.
As a result, you can compare the pre-service and post-service states
of the context to measure the performance of various components, etc.

Some extractors, like `get_current_label`, have restrictions in terms of their
run stage: for instance, `get_current_label` needs to only be used as an
`after_handler` to function correctly.

"""
# %%
pipeline = Pipeline.model_validate(
    {
        "script": TOY_SCRIPT,
        "start_label": ("greeting_flow", "start_node"),
        "fallback_label": ("greeting_flow", "fallback_node"),
        "pre_services": ServiceGroup(
            before_handler=[default_extractors.get_timing_before],
            after_handler=[
                get_service_state,
                default_extractors.get_timing_after,
            ],
            components=[
                {"handler": heavy_service},
                {"handler": heavy_service},
            ],
        ),
    }
)
# These are Extra Handlers for Actor.
pipeline.actor.add_extra_handler(
    GlobalExtraHandlerType.BEFORE, default_extractors.get_timing_before
)
pipeline.actor.add_extra_handler(
    GlobalExtraHandlerType.AFTER, get_service_state
)
pipeline.actor.add_extra_handler(
    GlobalExtraHandlerType.AFTER, default_extractors.get_current_label
)
pipeline.actor.add_extra_handler(
    GlobalExtraHandlerType.AFTER, default_extractors.get_timing_after
)

# These are global Extra Handlers for Pipeline.
pipeline.add_global_handler(
    GlobalExtraHandlerType.BEFORE_ALL, default_extractors.get_timing_before
)
pipeline.add_global_handler(
    GlobalExtraHandlerType.AFTER_ALL, default_extractors.get_timing_after
)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, get_service_state)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        pipeline.run()
