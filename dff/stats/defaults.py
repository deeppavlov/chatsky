"""
Default Extractors
------------------
This module includes a pool of default extractors
that you can use out of the box.

The default configuration for Superset dashboard leverages the data collected
by the extractors below. In order to use the default charts,
make sure that you include those functions in your pipeline.
Detailed examples can be found in the `tutorials` section.

"""
from datetime import datetime

from dff.script import Context
from dff.pipeline import ExtraHandlerRuntimeInfo
from .pool import StatsExtractorPool
from .record import StatsRecord
from .utils import get_wrapper_field

default_extractor_pool = StatsExtractorPool()


@default_extractor_pool.add_after_extractor
async def extract_current_label(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    """
    Extract the current label on each turn.
    This function is required for running the dashboard with the default configuration.
    """
    last_label = ctx.last_label
    if last_label is None:
        return StatsRecord.from_context(ctx, info, {"flow": None, "node": None, "label": None})
    return StatsRecord.from_context(
        ctx, info, {"flow": last_label[0], "node": last_label[1], "label": ": ".join(last_label)}
    )


@default_extractor_pool.add_before_extractor
async def extract_timing(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    """
    Extract the pipeline component's start time.
    This function is required for running the dashboard with the default configuration.
    """
    start_time = datetime.now()
    ctx.misc[get_wrapper_field(info, "time")] = start_time


@default_extractor_pool.add_after_extractor
async def extract_timing(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    """
    Extract the pipeline component's finish time.
    This function is required for running the dashboard with the default configuration.
    """
    start_time = ctx.misc[get_wrapper_field(info, "time")]
    data = {"execution_time": str(datetime.now() - start_time)}
    group_stats = StatsRecord.from_context(ctx, info, data)
    return group_stats
