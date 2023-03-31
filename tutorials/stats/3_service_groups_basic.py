# %% [markdown]
"""
# 3. Service Groups Basic

The following example shows how to collect statistics of service groups.
"""


# %%
import os
import asyncio

from dff.script import Context
from dff.pipeline import Pipeline, ACTOR, ServiceGroup, ExtraHandlerRuntimeInfo
from dff.stats import StatsStorage, StatsRecord, ExtractorPool
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
Handlers can be applied to any pipeline parameter, including service groups.
The `ServiceGroup` constructor has `before_handler` and `after_handler` parameters,
to which handler functions can be passed.

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
                after_handler=[get_group_stats],
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
    pipeline.run()
