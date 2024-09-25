# %% [markdown]
"""
# 7. Extra Handlers and Extensions

The following tutorial shows how pipeline can be extended
by global extra handlers and custom functions.

Here, %mddoclink(api,core.pipeline,Pipeline.add_global_handler)
function is shown, that can be used to add extra handlers before
and/or after all pipeline services.
"""

# %pip install chatsky

# %%
import asyncio
import json
import random
import logging
import sys
from importlib import reload
from datetime import datetime

from chatsky.core.service import (
    GlobalExtraHandlerType,
    ExtraHandlerRuntimeInfo,
    Service,
)
from chatsky import Pipeline, Context
from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
)
from chatsky.utils.testing.toy_script import HAPPY_PATH, TOY_SCRIPT

reload(logging)
logging.basicConfig(
    stream=sys.stdout, level=logging.INFO
)
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
Actually, `BEFORE_ALL` and `AFTER_ALL`
    are attached to root service group named 'pipeline',
    so they return its runtime info

All extra handlers warnings (see tutorial 7)
are applicable to global extra handlers.
Pipeline `add_global_extra_handler` function is used to register
    global extra handlers. It accepts following arguments:

* `global_extra_handler_type` (required) - A `GlobalExtraHandlerType` instance,
    indicates extra handler type to add.
* `extra_handler` (required) - The `ExtraHandlerFunction` itself.
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
that run for a random amount of time between 0 and 0.05 seconds.
"""

# %%


def before_all(ctx: Context, info: ExtraHandlerRuntimeInfo):
    now = datetime.now()
    ctx.misc["pipeline_info"] = {"start_time": now}
    ctx.misc["start_times"] = {info.component.path: now}


def before(ctx: Context, info: ExtraHandlerRuntimeInfo):
    ctx.misc["start_times"].update({info.component.path: datetime.now()})


def after(ctx: Context, info: ExtraHandlerRuntimeInfo):
    start_time = ctx.misc["start_times"][info.component.path]
    ctx.misc["pipeline_info"].update(
        {
            f"{info.component.path}_duration": datetime.now() - start_time,
            f"{info.component.path}_state": info.component.get_state(ctx),
        }
    )


def after_all(ctx: Context, info: ExtraHandlerRuntimeInfo):
    ctx.misc["pipeline_info"].update(
        {"total_time": datetime.now() - ctx.misc["start_times"][info.component.path]}
    )
    pipeline_info = ctx.misc["pipeline_info"]
    logger.info(
        f"Pipeline stats: {json.dumps(pipeline_info, indent=4, default=str)}"
    )


class LongService(Service):
    async def call(self, _: Context):
        timeout = random.randint(0, 5) / 100
        logger.info(
            f"Service {self.name} is going to sleep for {timeout} seconds."
        )
        await asyncio.sleep(timeout)


# %%
pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "pre_services": [LongService() for _ in range(0, 5)],
}

# %%
pipeline = Pipeline(**pipeline_dict)

pipeline.add_global_handler(GlobalExtraHandlerType.BEFORE_ALL, before_all)
pipeline.add_global_handler(GlobalExtraHandlerType.BEFORE, before)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER, after)
pipeline.add_global_handler(GlobalExtraHandlerType.AFTER_ALL, after_all)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH, printout=True)
    if is_interactive_mode():
        pipeline.run()
