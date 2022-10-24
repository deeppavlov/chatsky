import sys
import asyncio
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))

from df_engine.core import Context, Actor
from df_runner import Pipeline, WrapperRuntimeInfo, GlobalWrapperType, to_service
from df_stats import StatsStorage, StatsRecord, ExtractorPool

from _utils import parse_args, script

extractor_pool = ExtractorPool()


async def heavy_service(_):
    await asyncio.sleep(random.randint(0, 2))


@extractor_pool.new_extractor
async def get_pipeline_state(ctx: Context, _, info: WrapperRuntimeInfo):
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
pipeline.add_global_wrapper(GlobalWrapperType.AFTER_ALL, get_pipeline_state)

if __name__ == "__main__":
    args = parse_args()
    stats = StatsStorage.from_uri(args["uri"], table=args["table"])
    stats.add_extractor_pool(extractor_pool)
    pipeline.run()
