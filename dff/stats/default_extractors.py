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
from .utils import get_wrapper_field


async def get_current_label(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    """
    Extract the current label on each turn.
    This function is required for running the dashboard with the default configuration.
    """
    last_label = ctx.last_label
    if last_label is None:
        return {"flow": None, "node": None, "label": None}
    return {"flow": last_label[0], "node": last_label[1], "label": ": ".join(last_label)}


async def get_timing_before(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    """
    Extract the pipeline component's start time.
    This function is required for running the dashboard with the default configuration.

    The function leverages the `framework_states` field of the context to store results.
    As a result, the function output is cleared on every turn and does not get persisted
    to the context storage.
    """
    start_time = datetime.now()
    ctx.framework_states[get_wrapper_field(info, "time")] = start_time


async def get_timing_after(ctx: Context, _, info: ExtraHandlerRuntimeInfo):  # noqa: F811
    """
    Extract the pipeline component's finish time.
    This function is required for running the dashboard with the default configuration.

    The function leverages the `framework_states` field of the context to store results.
    As a result, the function output is cleared on every turn and does not get persisted
    to the context storage.
    """
    start_time = ctx.framework_states[get_wrapper_field(info, "time")]
    data = {"execution_time": str(datetime.now() - start_time)}
    return data
