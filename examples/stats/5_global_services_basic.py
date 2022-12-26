# %% [markdown]
"""
# 5. Global Services Basic

The following example shows how to collect statistics
of global services.
"""


# %%
import asyncio

from dff.script import Context, Actor
from dff.pipeline import Pipeline, ExtraHandlerRuntimeInfo, GlobalExtraHandlerType
from dff.stats import StatsStorage, StatsRecord, ExtractorPool
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.utils.testing.stats_cli import parse_args


# %% [markdown]
"""
Like with regular handlers, you can define global statistic handlers,
which will be applied to every element inside the pipeline.

Use the `add_global_handler` method provided by the `Pipeline` class.
"""


# %%
extractor_pool = ExtractorPool()


async def heavy_service(_):
    await asyncio.sleep(0.02)


@extractor_pool.new_extractor
async def get_pipeline_state(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    data = {"runtime_state": info["component"]["execution_state"]}
    group_stats = StatsRecord.from_context(ctx, info, data)
    return group_stats


# %%
actor = Actor(
    TOY_SCRIPT,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

pipeline_dict = {
    "components": [
        [heavy_service for _ in range(0, 5)],
        actor,
    ],
}
pipeline = Pipeline.from_dict(pipeline_dict)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, get_pipeline_state)

if __name__ == "__main__":
    args = parse_args()
    stats = StatsStorage.from_uri(args["uri"], table=args["table"])
    stats.add_extractor_pool(extractor_pool)
    pipeline.run()
