# %% [markdown]
"""
# 6. Extra Handlers (full)

The following tutorial shows extra handlers possibilities and use cases.

This tutorial is a more advanced version of the
[previous tutorial](%doclink(tutorial,pipeline.6_extra_handlers_basic)).
"""

# %pip install chatsky psutil

# %%
import json
import random
import logging
import sys
from importlib import reload
from datetime import datetime

import psutil

from chatsky.core.service import (
    ServiceGroup,
    ExtraHandlerRuntimeInfo,
    to_service,
    Service,
)
from chatsky import Context, Pipeline
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
Extra handlers are additional function lists
    (before-functions and/or after-functions)
    that can be added to any pipeline components (service and service groups).
Despite extra handlers can be used to prepare data for certain services,
that require some very special input type,
    in most cases services should be preferred for that purpose.
Extra handlers can be asynchronous,
however there's no statistics that can be collected about them.
So their main purpose should be _really_ lightweight data conversion (etc.)
    operations or service and service groups statistics collection.

Extra handlers have the following constructor arguments / parameters:

* `functions` - Functions that will be run.
* `timeout` - Timeout for that extra handler
        (for asynchronous extra handlers only).
* `asynchronous` - A flag that indicates whether the `functions`
        should be executed asynchronously. The default value
        of the flag is False.
NB! Extra handlers don't have execution state,
so their names shouldn't appear in built-in condition functions.

Extra handlers callable signature can be one of the following:
`[ctx]` or `[ctx, info]`, where:

* `ctx` - `Context` of the current dialog.
* `info` - Dictionary, containing information about current extra handler
            and the `self` object of this pipeline component.
            For example, `info.stage` will tell you if this Extra Handler is a
            BeforeHandler or AfterHandler; `info.component.name` will give
            you the component's name; `info.component.get_state(ctx)` will
            return the component's execution state.

Extra handlers can be attached to a pipeline component in a few different ways:

1. Directly in constructor - by adding extra handlers to
    `before_handler` or `after_handler` constructor parameter.
2. (Services only) `to_service` decorator -
    transforms function to service with extra handlers
    from `before_handler` and `after_handler` arguments.
3. Using `add_extra_handler` function of `PipelineComponent`

Example:

    component.add_extra_handler(GlobalExtraHandlerType.AFTER, get_service_state)

`add_extra_handler(extra_handler_type, extra_handler_func, condition_func)`
can also be added recursively to all components of a `ServiceGroup` through
a condition function of the following signature:

    def cond_func(path: str) -> bool:

Basically, you can return `True` for some paths, and `False` for others,
adding your Extra Handler to the services you
want to measure on execution time, for example.

Here 5 `heavy_service`s fill big amounts of memory with random numbers.
Their runtime stats are captured and displayed by extra services,
`time_measure_handler` measures time and
`ram_measure_handler` - allocated memory.
Another `time_measure_handler` measures total
amount of time taken by all of them (combined in service group).
`logging_service` logs stats, however it can use string arguments only,
    so `json_encoder_handler` is applied to encode stats to JSON.
"""


# %%
def get_extra_handler_misc_field(
    info: ExtraHandlerRuntimeInfo, postfix: str
) -> str:  # This method calculates `misc` field name dedicated to extra handler
    # based on its and its service name
    return f"{info.component.name}-{postfix}"


def time_measure_before_handler(ctx, info):
    ctx.misc.update(
        {get_extra_handler_misc_field(info, "time"): datetime.now()}
    )


def time_measure_after_handler(ctx, info):
    ctx.misc.update(
        {
            get_extra_handler_misc_field(info, "time"): datetime.now()
            - ctx.misc[get_extra_handler_misc_field(info, "time")]
        }
    )


def ram_measure_before_handler(ctx, info):
    ctx.misc.update(
        {
            get_extra_handler_misc_field(
                info, "ram"
            ): psutil.virtual_memory().available
        }
    )


def ram_measure_after_handler(ctx, info):
    ctx.misc.update(
        {
            get_extra_handler_misc_field(info, "ram"): ctx.misc[
                get_extra_handler_misc_field(info, "ram")
            ]
            - psutil.virtual_memory().available
        }
    )


def json_converter_before_handler(ctx, info):
    ctx.misc.update(
        {
            get_extra_handler_misc_field(info, "str"): json.dumps(
                ctx.misc, indent=4, default=str
            )
        }
    )


def json_converter_after_handler(ctx, info):
    ctx.misc.pop(get_extra_handler_misc_field(info, "str"))


memory_heap = dict()  # This object plays part of some memory heap


# %%
@to_service(
    before_handler=[time_measure_before_handler, ram_measure_before_handler],
    after_handler=[time_measure_after_handler, ram_measure_after_handler],
)
def heavy_service(ctx: Context):
    memory_heap[ctx.last_request.text] = [
        random.randint(0, num) for num in range(0, 1000)
    ]


class LoggingService(Service):
    async def call(self, ctx: Context):
        str_misc = ctx.misc[f"{self.name}-str"]
        assert isinstance(str_misc, str)
        logger.info(f"Stringified misc: {str_misc}")


pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "pre_services": ServiceGroup(
        before_handler=[time_measure_before_handler],
        after_handler=[time_measure_after_handler],
        components=[heavy_service for _ in range(0, 5)],
    ),
    "post_services": LoggingService(
        before_handler=[json_converter_before_handler],
        after_handler=[json_converter_after_handler],
    ),
}

# %%
pipeline = Pipeline(**pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH, printout=True)
    if is_interactive_mode():
        pipeline.run()
