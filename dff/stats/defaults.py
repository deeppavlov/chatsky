"""
Defaults
*********

This module includes default utilities which you can use out of the box.
"""
from datetime import datetime

from df_engine.core import Context
from df_runner import WrapperRuntimeInfo
from .pool import ExtractorPool
from .record import StatsRecord
from .utils import get_wrapper_field

default_extractor_pool = ExtractorPool()


@default_extractor_pool.new_extractor
async def extract_current_label(ctx: Context, _, info: WrapperRuntimeInfo):
    last_label = ctx.last_label or ("", "")
    default_data = StatsRecord.from_context(
        ctx, info, {"flow": last_label[0], "node": last_label[1], "label": ": ".join(last_label)}
    )
    return default_data


@default_extractor_pool.new_extractor
async def extract_timing_before(ctx: Context, _, info: WrapperRuntimeInfo):
    start_time = datetime.now()
    ctx.misc[get_wrapper_field(info, "time")] = start_time


@default_extractor_pool.new_extractor
async def extract_timing_after(ctx: Context, _, info: WrapperRuntimeInfo):
    start_time = ctx.misc[get_wrapper_field(info, "time")]
    data = {"execution_time": datetime.now() - start_time}
    group_stats = StatsRecord.from_context(ctx, info, data)
    return group_stats
