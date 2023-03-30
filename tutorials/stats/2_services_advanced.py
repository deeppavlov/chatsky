# %% [markdown]
"""
# 2. Services Advanced

The following examples shows how to decorate several functions
for statistics collection.
"""


# %%
import asyncio

from dff.script import Context, Actor
from dff.pipeline import Pipeline, Service, ExtraHandlerRuntimeInfo, to_service
from dff.stats import StatsStorage, ExtractorPool, StatsRecord
from dff.stats import default_extractor_pool  # import default pool from addon
from dff.utils.testing.toy_script import TOY_SCRIPT


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
extractor_pool = ExtractorPool()


@extractor_pool.new_extractor
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
    before_handler=[default_extractor_pool["extract_timing_before"]],
    after_handler=[get_service_state, default_extractor_pool["extract_timing_after"]],
)
async def heavy_service(ctx: Context, actor: Actor):
    _ = ctx  # get something from ctx if it needs
    _ = actor  # get something from actor if it needs
    await asyncio.sleep(0.02)


# %%
actor = Actor(
    TOY_SCRIPT,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

pipeline = Pipeline.from_dict(
    {
        "components": [
            Service(handler=heavy_service),  # add `heavy_service` before the actor
            Service(
                handler=to_service(
                    before_handler=[default_extractor_pool["extract_timing_before"]],
                    after_handler=[
                        get_service_state,
                        default_extractor_pool["extract_timing_after"],
                    ],
                )(
                    actor
                )  # wrap and add the actor
            ),
        ]
    }
)


if __name__ == "__main__":
    from dff.utils.testing.stats_cli import parse_args

    args = parse_args()
    stats = StatsStorage.from_uri(args["uri"], table=args["table"])
    stats.add_extractor_pool(extractor_pool)
    stats.add_extractor_pool(default_extractor_pool)
    pipeline.run()
