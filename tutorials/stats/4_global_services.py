# %% [markdown]
"""
# 4. Global Services

The following example demonstrates how to collect statistics
from several global services.
"""


# %%
import os
import asyncio

from dff.script import Context
from dff.pipeline import Pipeline, ACTOR, ExtraHandlerRuntimeInfo, GlobalExtraHandlerType
from dff.stats import StatsStorage, StatsExtractorPool, StatsRecord, default_extractor_pool
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.utils.testing.common import is_interactive_mode


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
extractor_pool = StatsExtractorPool()


async def heavy_service(_):
    await asyncio.sleep(0.02)


@extractor_pool.add_extractor("after")
async def get_pipeline_state(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    data = {"runtime_state": info["component"]["execution_state"]}
    group_stats = StatsRecord.from_context(ctx, info, data)
    return group_stats


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
pipeline.add_global_handler(
    GlobalExtraHandlerType.BEFORE_ALL, default_extractor_pool["before"]["extract_timing"]
)
pipeline.add_global_handler(
    GlobalExtraHandlerType.AFTER_ALL, default_extractor_pool["after"]["extract_timing"]
)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, get_pipeline_state)

if __name__ == "__main__":
    if is_interactive_mode():
        from dff.utils.testing.stats_cli import parse_args

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
