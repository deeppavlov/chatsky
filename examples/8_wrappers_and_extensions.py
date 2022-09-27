"""
Wrappers and extensions
=======================

The following example shows how pipeline can be extended by global wrappers and custom functions
"""

import asyncio
import json
import logging
import random
from datetime import datetime

from df_engine.core import Actor

from df_pipeline import Pipeline, ComponentExecutionState, GlobalWrapperType, WrapperRuntimeInfo, ServiceRuntimeInfo
from _utils import SCRIPT, get_auto_arg, auto_run_pipeline

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

""" TODO: update docs
Pipeline functionality can be extended by global wrappers.
Global wrappers are special wrappers that are called on some stages of pipeline execution.
There are 4 types of global wrappers:
    `BEFORE_ALL` - is called before pipeline execution
    `BEFORE` - is called before each service and service group execution
    `AFTER` - is called after each service and service group execution
    `AFTER_ALL` - is called after pipeline execution
Global wrappers have the same signature as regular wrappers.
Actually `BEFORE_ALL` and `AFTER_ALL` are attached to root service group named 'pipeline', so they return its runtime info

All wrappers warnings (see example №7) are applicable to global wrappers.
Pipeline `add_global_wrapper` function is used to register global wrappers. It accepts following arguments:
    `global_wrapper_type` (required) - a GlobalWrapperType instance, indicates wrapper type to add
    `wrapper` (required) - the wrapper function itself
    `whitelist` - an optional list of paths, if it's not None the wrapper will be applied to specified pipeline components only
    `blacklist` - an optional list of paths, if it's not None the wrapper will be applied to all pipeline components except specified

Here basic functionality of `df-node-stats` library is emulated.
Information about pipeline component execution time and result is collected and printed to info log after pipeline execution.
Pipeline consists of actor and 25 `long_service`s that run random amount of time between 0 and 5 seconds.
"""


actor = Actor(
    SCRIPT,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

start_times = dict()  # Place to temporarily store service start times
pipeline_info = dict()  # Pipeline information storage


def before_all(_, __, info: WrapperRuntimeInfo):
    global start_times, pipeline_info
    now = datetime.now()
    pipeline_info = {"start_time": now}
    start_times = {info["component"]["path"]: now}


def before(_, __, info: WrapperRuntimeInfo):
    start_times.update({info["component"]["path"]: datetime.now()})


def after(_, __, info: WrapperRuntimeInfo):
    start_time = start_times[info["component"]["path"]]
    pipeline_info.update(
        {
            f"{info['component']['path']}_duration": datetime.now() - start_time,
            f"{info['component']['path']}_success": info["component"]["execution_state"].get(
                info["component"]["path"], ComponentExecutionState.NOT_RUN.name
            ),
        }
    )


def after_all(_, __, info: WrapperRuntimeInfo):
    pipeline_info.update({f"total_time": datetime.now() - start_times[info["component"]["path"]]})
    logger.info(f"Pipeline stats: {json.dumps(pipeline_info, indent=4, default=str)}")


async def long_service(_, __, info: ServiceRuntimeInfo):
    timeout = random.randint(0, 5)
    logger.info(f"Service {info['name']} is going to sleep for {timeout} seconds.")
    await asyncio.sleep(timeout)


pipeline_dict = {
    "components": [
        [long_service for _ in range(0, 25)],
        actor,
    ],
}


pipeline = Pipeline(**pipeline_dict)

pipeline.add_global_wrapper(GlobalWrapperType.BEFORE_ALL, before_all)
pipeline.add_global_wrapper(GlobalWrapperType.BEFORE, before)
pipeline.add_global_wrapper(GlobalWrapperType.AFTER, after)
pipeline.add_global_wrapper(GlobalWrapperType.AFTER_ALL, after_all)

if __name__ == "__main__":
    if get_auto_arg():
        auto_run_pipeline(pipeline, logger=logger)
    else:
        pipeline.run()
