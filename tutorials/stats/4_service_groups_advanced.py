# %% [markdown]
"""
# 4. Service Groups Advanced

The following examples illustrates how to obtain statistics from
several service groups.
"""


# %%
import os
import asyncio

from dff.script import Context
from dff.pipeline import Pipeline, ACTOR, ServiceGroup, ExtraHandlerRuntimeInfo
from dff.stats import StatsStorage, StatsRecord, ExtractorPool, default_extractor_pool
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
You can also collect statistics of service groups that consist of multiple services.
This can be done in the manner demonstrated below.
"""


# %%
extractor_pool = ExtractorPool()


async def heavy_service(_):
    await asyncio.sleep(0.02)


@extractor_pool.new_extractor
async def get_group_stats(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    data = {"runtime_state": info["component"]["execution_state"]}
    group_stats = StatsRecord.from_context(ctx, info, data)
    return group_stats


# %%
pipeline = Pipeline.from_dict(
    {
        "script": TOY_SCRIPT,
        "start_label": ("greeting_flow", "start_node"),
        "fallback_label": ("greeting_flow", "fallback_node"),
        "components": [
            ServiceGroup(
                before_handler=[default_extractor_pool["extract_timing_before"]],
                after_handler=[default_extractor_pool["extract_timing_after"], get_group_stats],
                components=[{"handler": heavy_service}, {"handler": heavy_service}],
            ),
            ACTOR,
        ],
    }
)

if __name__ == "__main__":
    from dff.utils.testing.stats_cli import parse_args

    if is_interactive_mode():
        uri = "clickhouse://{0}:{1}@localhost:8123/{2}".format(
            os.getenv("CLICKHOUSE_USER"),
            os.getenv("CLICKHOUSE_PASSWORD"),
            os.getenv("CLICKHOUSE_DB"),
        )
    else:
        args = parse_args()
        uri = args["uri"]
    stats = StatsStorage.from_uri(uri)
    stats.add_extractor_pool(extractor_pool)
    stats.add_extractor_pool(default_extractor_pool)
    pipeline.run()
