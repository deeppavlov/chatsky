# %% [markdown]
"""
# 8. Extra Handlers and Extensions

The following example shows how pipeline can be extended
by global extra handlers and custom functions.
"""


# %%
import asyncio
import json
import logging
import random
from datetime import datetime

from dff.core.engine.core import Actor
from dff.core.pipeline import (
    Pipeline,
    ComponentExecutionState,
    GlobalExtraHandlerType,
    ExtraHandlerRuntimeInfo,
    ServiceRuntimeInfo,
)

from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import HAPPY_PATH, TOY_SCRIPT

logger = logging.getLogger(__name__)

# %% [markdown]
"""
Pipeline functionality can be extended by global extra handlers.
Global extra handlers are special extra handlers
    that are called on some stages of pipeline execution.
There are 4 types of global extra handlers:

    * `BEFORE_ALL` is called before pipeline execution.
    * `BEFORE` is called before each service and service group execution.
    * `AFTER` is called after each service and service group execution.
    * `AFTER_ALL` is called after pipeline execution.

Global extra handlers have the same signature as regular extra handlers.
Actually `BEFORE_ALL` and `AFTER_ALL`
    are attached to root service group named 'pipeline',
    so they return its runtime info

All extra handlers warnings (see example 7)
are applicable to global extra handlers.
Pipeline `add_global_extra_handler` function is used to register
    global extra handlers. It accepts following arguments:

* `global_extra_handler_type` (required) - A `GlobalExtraHandlerType` instance,
    indicates extra handler type to add.
* `extra_handler` (required) - The extra handler function itself.
* `whitelist` - An optional list of paths, if it's not `None`
                the extra handlers will be applied to
                specified pipeline components only.
* `blacklist` - An optional list of paths, if it's not `None`
                the extra handlers will be applied to
                all pipeline components except specified.

Here basic functionality of `df-node-stats` library is emulated.
Information about pipeline component execution time and
    result is collected and printed to info log after pipeline execution.
Pipeline consists of actor and 25 `long_service`s
that run random amount of time between 0 and 0.05 seconds.
"""

# %%
start_times = dict()  # Place to temporarily store service start times
pipeline_info = dict()  # Pipeline information storage


def before_all(_, __, info: ExtraHandlerRuntimeInfo):
    global start_times, pipeline_info
    now = datetime.now()
    pipeline_info = {"start_time": now}
    start_times = {info["component"]["path"]: now}


def before(_, __, info: ExtraHandlerRuntimeInfo):
    start_times.update({info["component"]["path"]: datetime.now()})


def after(_, __, info: ExtraHandlerRuntimeInfo):
    start_time = start_times[info["component"]["path"]]
    pipeline_info.update(
        {
            f"{info['component']['path']}_duration": datetime.now() - start_time,
            f"{info['component']['path']}_success": info["component"]["execution_state"].get(
                info["component"]["path"], ComponentExecutionState.NOT_RUN.name
            ),
        }
    )


def after_all(_, __, info: ExtraHandlerRuntimeInfo):
    pipeline_info.update({"total_time": datetime.now() - start_times[info["component"]["path"]]})
    logger.info(f"Pipeline stats: {json.dumps(pipeline_info, indent=4, default=str)}")


async def long_service(_, __, info: ServiceRuntimeInfo):
    timeout = random.randint(0, 5) / 100
    logger.info(f"Service {info['name']} is going to sleep for {timeout} seconds.")
    await asyncio.sleep(timeout)


# %%
actor = Actor(
    TOY_SCRIPT,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)


pipeline_dict = {
    "components": [
        [long_service for _ in range(0, 25)],
        actor,
    ],
}

# %%
pipeline = Pipeline(**pipeline_dict)

pipeline.add_global_handler(GlobalExtraHandlerType.BEFORE_ALL, before_all)
pipeline.add_global_handler(GlobalExtraHandlerType.BEFORE, before)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER, after)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, after_all)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
