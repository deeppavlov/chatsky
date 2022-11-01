import sys
import asyncio
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))

from dff.core.engine.core import Context, Actor
from dff.core.pipeline import Pipeline, ExtraHandlerRuntimeInfo, GlobalExtraHandlerType
from dff.stats import StatsStorage, ExtractorPool, StatsRecord, default_extractor_pool

from _stats_utils import parse_args, script

"""
Like with regular handlers, you can define global statistic handlers, 
which will be applied to every element inside the pipeline.

Use the `add_global_handler` method.
"""


extractor_pool = ExtractorPool()


async def heavy_service(_):
    await asyncio.sleep(random.randint(0, 2))


@extractor_pool.new_extractor
async def get_pipeline_state(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    data = {"runtime_state": info["component"]["execution_state"]}
    group_stats = StatsRecord.from_context(ctx, info, data)
    return group_stats


actor = Actor(script, ("root", "start"), ("root", "fallback"))

pipeline_dict = {
    "components": [
        [heavy_service for _ in range(0, 5)],
        actor,
    ],
}
pipeline = Pipeline.from_dict(pipeline_dict)
pipeline.add_global_handler(GlobalExtraHandlerType.BEFORE_ALL, default_extractor_pool["extract_timing_before"])
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, default_extractor_pool["extract_timing_after"])
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, get_pipeline_state)

if __name__ == "__main__":
    args = parse_args()
    stats = StatsStorage.from_uri(args["uri"], table=args["table"])
    stats.add_extractor_pool(extractor_pool)
    stats.add_extractor_pool(default_extractor_pool)
    pipeline.run()
