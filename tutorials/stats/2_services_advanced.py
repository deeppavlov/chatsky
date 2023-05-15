# %% [markdown]
"""
# 2. Services Advanced

The following examples shows how to decorate several functions
for statistics collection.
"""


# %%
import os
import asyncio

from dff.script import Context
from dff.pipeline import Pipeline, ACTOR, Service, ExtraHandlerRuntimeInfo, to_service
from dff.stats import StatsStorage, StatsExtractorPool, StatsRecord
from dff.stats import default_extractor_pool  # import default pool from addon
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.utils.testing.common import is_interactive_mode


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
extractor_pool = StatsExtractorPool()


@extractor_pool.add_after_extractor
async def get_service_state(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    # extract execution state of service from info
    data = {
        "execution_state": info["component"]["execution_state"],
    }
    # return a record to save into connected database
    return StatsRecord.from_context(ctx, info, data)


# %%
# use together extractor_pool and default_extractor_pool
# run extract_timing_before before `heavy_service`
# run get_service_state and extract_timing_after after `heavy_service`
@to_service(
    before_handler=[default_extractor_pool["before"]["extract_timing"]],
    after_handler=[get_service_state, default_extractor_pool["after"]["extract_timing"]],
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
                    before_handler=[default_extractor_pool["before"]["extract_timing"]],
                    after_handler=[
                        get_service_state,
                        default_extractor_pool["after"]["extract_timing"],
                    ],
                )(
                    ACTOR
                )  # wrap and add the actor
            ),
        ],
    }
)


if __name__ == "__main__":
    from dff.utils.testing.stats_cli import parse_args

    if is_interactive_mode():
        args = parse_args()
        uri = args["uri"]
    else:
        uri = "clickhouse://{0}:{1}@localhost:8123/{2}".format(
            os.getenv("CLICKHOUSE_USER"),
            os.getenv("CLICKHOUSE_PASSWORD"),
            os.getenv("CLICKHOUSE_DB"),
        )
    stats_storage = StatsStorage.from_uri(uri)
    extractor_pool.add_subscriber(stats_storage)
    default_extractor_pool.add_subscriber(stats_storage)
    pipeline.run()
