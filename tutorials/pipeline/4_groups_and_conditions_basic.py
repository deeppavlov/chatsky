# %% [markdown]
"""
# 4. Groups and conditions (basic)

The following example shows `pipeline` service group usage and start conditions.

Here, %mddoclink(api,core.service.service,Service)s
and %mddoclink(api,core.service.group,ServiceGroup)s
are shown for advanced data pre- and postprocessing based on conditions.
"""

# %pip install chatsky

# %%
import logging
import sys
from importlib import reload

from chatsky.core import Context
from chatsky.core.service import Service
from chatsky.conditions import Not, ServiceFinished
from chatsky import Pipeline

from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
)
from chatsky.utils.testing.toy_script import HAPPY_PATH, TOY_SCRIPT

reload(logging)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="")
logger = logging.getLogger(__name__)


# %% [markdown]
"""
Pipeline can contain not only single services, but also service groups.
Service groups can be defined as `ServiceGroup` objects:
      lists of `Service` or more `ServiceGroup` objects.
`ServiceGroup` objects should contain `components` -
a list of `Service` and `ServiceGroup` objects.

To receive serialized information about service,
    service group or pipeline `model_dump` method from Pydantic can be used,
    which returns important object properties as a dictionary.

Services and service groups can be executed conditionally.
Conditions are functions passed to `start_condition` argument.
They have the following signature

    class MyCondition(BaseCondition):
        async def call(self, ctx: Context) -> bool:

A `Service` is executed only if its `start_condition` returns `True`.
By default all the services start unconditionally.
There are several built-in condition functions available
(see `Script` [tutorial](%doclink(tutorial,script.core.2_conditions))).
One notable built-in condition is `ServiceFinished`
which returns `True` if a `Service` with a specified path
completed successfully and `False` otherwise.

`ServiceFinished` accepts the following constructor parameters:

* `path` (required) - a path to the `Service`.
* `wait` - A boolean flag indicating whether it should wait for the specified
        `Service` to complete (defaults to `True`).

In the following example, a conditionally executed service named
`never_running_service` is executed only if `always_running_service`
does not finish successfully (which should never happen).
The service named `context_printing_service`
prints pipeline runtime information,
including the execution state of all previously run services.
"""


# %%
class AlwaysRunningService(Service):
    async def call(self, _: Context):
        logger.info(f"Service '{self.name}' is running...")


class NeverRunningService(Service):
    async def call(self, _: Context):
        raise Exception(f"Oh no! The '{self.name}' service is running!")


class RuntimeInfoPrintingService(Service):
    async def call(self, _: Context):
        logger.info(
            f"Service '{self.name}' runtime execution info:"
            f"{self.model_dump_json(indent=4)}"
        )


# %%
pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "pre_services": AlwaysRunningService(
        name="always_running_service",
    ),
    "post_services": [
        NeverRunningService(
            start_condition=Not(
                ServiceFinished(
                    ".pipeline.pre.always_running_service"
                )  # pre services belong to the "pre" group; post -- to "post"
            ),
        ),
        RuntimeInfoPrintingService(
            name="runtime_info_printing_service",
        ),
    ],
}


# %%
pipeline = Pipeline.model_validate(pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH, printout=True)
    if is_interactive_mode():
        pipeline.run()
