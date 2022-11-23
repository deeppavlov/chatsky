import asyncio

from dff.core.engine.core import Context, Actor
from dff.core.pipeline import Pipeline, ServiceGroup, ExtraHandlerRuntimeInfo
from dff.stats import StatsStorage, StatsRecord, ExtractorPool, default_extractor_pool
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.utils.testing.stats_cli import parse_args


extractor_pool = ExtractorPool()


async def heavy_service(_):
    await asyncio.sleep(0.02)


@extractor_pool.new_extractor
async def get_group_stats(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    data = {"runtime_state": info["component"]["execution_state"]}
    group_stats = StatsRecord.from_context(ctx, info, data)
    return group_stats


actor = Actor(
    TOY_SCRIPT,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

pipeline = Pipeline.from_dict(
    {
        "components": [
            ServiceGroup(
                before_handler=[default_extractor_pool["extract_timing_before"]],
                after_handler=[default_extractor_pool["extract_timing_after"], get_group_stats],
                components=[{"handler": heavy_service}, {"handler": heavy_service}],
            ),
            actor,
        ],
    }
)

if __name__ == "__main__":
    args = parse_args()
    stats = StatsStorage.from_uri(args["uri"], table=args["table"])
    stats.add_extractor_pool(extractor_pool)
    stats.add_extractor_pool(default_extractor_pool)
    pipeline.run()
