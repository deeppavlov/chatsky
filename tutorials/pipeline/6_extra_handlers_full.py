# %% [markdown]
"""
# 6. Extra Handlers (full)

The following tutorial shows extra handlers possibilities and use cases.

This tutorial is a more advanced version of the
[previous tutorial](%doclink(tutorial,pipeline.6_extra_handlers_basic)).
"""

# %pip install dff psutil

# %%
import json
import logging
import random
from datetime import datetime

import psutil
from dff.script import Context

from dff.pipeline import (
    Pipeline,
    ServiceGroup,
    to_service,
    ExtraHandlerRuntimeInfo,
    ServiceRuntimeInfo,
    ACTOR,
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
* `asynchronous` - Whether this extra handler should be asynchronous or not.
NB! Extra handlers don't have execution state,
so their names shouldn't appear in built-in condition functions.

Extra handlers callable signature can be one of the following:
`[ctx]`, `[ctx, pipeline]` or `[ctx, pipeline, info]`, where:

* `ctx` - `Context` of the current dialog.
* `pipeline` - The current pipeline.
* `info` - Dictionary, containing information about current extra handler
            and pipeline execution state (see tutorial 4).

Extra handlers can be attached to pipeline component in a few different ways:

1. Directly in constructor - by adding extra handlers to
    `before_handler` or `after_handler` constructor parameter.
2. (Services only) `to_service` decorator -
    transforms function to service with extra handlers
    from `before_handler` and `after_handler` arguments.

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


def time_measure_before_handler(ctx, _, info):
    ctx.misc.update(
        {get_extra_handler_misc_field(info, "time"): datetime.now()}
    )


def time_measure_after_handler(ctx, _, info):
    ctx.misc.update(
        {
            get_extra_handler_misc_field(info, "time"): datetime.now()
            - ctx.misc[get_extra_handler_misc_field(info, "time")]
        }
    )


def ram_measure_before_handler(ctx, _, info):
    ctx.misc.update(
        {
            get_extra_handler_misc_field(
                info, "ram"
            ): psutil.virtual_memory().available
        }
    )


def ram_measure_after_handler(ctx, _, info):
    ctx.misc.update(
        {
            get_extra_handler_misc_field(info, "ram"): ctx.misc[
                get_extra_handler_misc_field(info, "ram")
            ]
            - psutil.virtual_memory().available
        }
    )


def json_converter_before_handler(ctx, _, info):
    ctx.misc.update(
        {
            get_extra_handler_misc_field(info, "str"): json.dumps(
                ctx.misc, indent=4, default=str
            )
        }
    )


def json_converter_after_handler(ctx, _, info):
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


@to_service(
    before_handler=[json_converter_before_handler],
    after_handler=[json_converter_after_handler],
)
def logging_service(ctx: Context, _, info: ServiceRuntimeInfo):
    str_misc = ctx.misc[f"{info.name}-str"]
    assert isinstance(str_misc, str)
    print(f"Stringified misc: {str_misc}")


pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "components": [
        ServiceGroup(
            before_handler=[time_measure_before_handler],
            after_handler=[time_measure_after_handler],
            components=[heavy_service for _ in range(0, 5)],
        ),
        ACTOR,
        logging_service,
    ],
}

# %%
pipeline = Pipeline(**pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
