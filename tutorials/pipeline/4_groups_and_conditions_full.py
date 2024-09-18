# %% [markdown]
"""
# 4. Groups and conditions (full)

The following tutorial shows `pipeline`
service group usage and start conditions.

This tutorial is a more advanced version of the
[previous tutorial](%doclink(tutorial,pipeline.4_groups_and_conditions_basic)).
"""

# %pip install chatsky

# %%
import logging

from chatsky.core import Context
from chatsky.conditions import Not, All
from chatsky.core.service import ServiceFinishedCondition, Service, ServiceGroup
from chatsky import Pipeline

from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
)
from chatsky.utils.testing.toy_script import HAPPY_PATH, TOY_SCRIPT

logger = logging.getLogger(__name__)

# %% [markdown]
"""
Pipeline can contain not only single services, but also service groups.
Service groups can be defined as `ServiceGroup` objects:
      lists of `Service` or more `ServiceGroup` objects.
`ServiceGroup` objects should contain `components` -
a list of `Service` and `ServiceGroup` objects.

Pipeline can contain not only single services, but also service groups.
Service groups can be defined as lists of `Service`
 or more `ServiceGroup` objects.
    (in fact, all of the pipeline services are combined
    into root service group named "pipeline").
Alternatively, the groups can be defined as objects
    with following constructor arguments:

* `components` (required) - A list of `Service` objects,
    `ServiceGroup` objects.
* `before_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See tutorials 6 and 7.
* `after_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See tutorials 6 and 7.
* `timeout` - Pipeline timeout, see tutorial 5.
* `asynchronous` - Whether or not this service group should be
    asynchronous to other components
* `all_async` - Whether or not this service group should run
    all it's components asynchronously.
* `start_condition` - Service group start condition.
* `name` - Custom defined name for the service group
    (keep in mind that names in one ServiceGroup should be unique).

Service (and service group) object fields
are mostly the same as constructor parameters,
however there are some differences:

* `path` - Contains globally unique (for pipeline)
    path to the service or service group.

If no name is specified for a service or service group,
    the name will be generated according to the following rules:

1. If service's handler is callable,
    service will be named callable.
2. Service group will be named 'service_group'.
3. Otherwise, it will be named 'noname_service'.
4. After that an index will be added to service name.

To receive serialized information about service, service group
or pipeline a property `info_dict` can be used,
it returns important object properties as a dict.
In addition to that `pretty_format` method of Pipeline
can be used to get all pipeline properties as a formatted string
(e.g. for logging or debugging purposes).

Services and service groups can be executed conditionally.
Conditions are functions passed to `start_condition` argument.
They have the following signature

    class MyCondition(BaseCondition):
        async def call(self, ctx: Context) -> bool:

Service is only executed if its start_condition returned `True`.
By default all the services start unconditionally.
There are number of built-in condition functions as well
as possibility to create custom ones. You can check which
condition functions are there in the `Script` tutorial about conditions,
or check the API directly.

There is also a built-in condition `ServiceFinishedCondition`
that returns `True` if a `Service` with a given path completed successfully,
returns `False` otherwise.

`ServiceFinishedCondition` accepts the following constructor parameters:

* `path` (required) - a path to the `Service`.
* `wait` - whether it should wait for the said `Service` to complete.
        defaults to `False`.

Custom condition functions can rely on data in `ctx.misc`
as well as on any external data source.
Built-in condition functions check other service states.
All of the services store their execution status in context,
    this status can be one of the following:

* `NOT_RUN` - Service hasn't bee executed yet.
* `RUNNING` - Service is currently being executed
    (important for asynchronous services).
* `FINISHED` - Service finished successfully.
* `FAILED` - Service execution failed (that also throws an exception).

Here there are two conditionally executed services:
a service named `running_service` is executed
    only if both `SimpleServices` in `service_group_0`
    are finished successfully.
`never_running_service` is executed only if `running_service` is not finished,
this should never happen.
`context_printing_service` prints pipeline runtime information,
    that contains execution state of all previously run services.
"""


# %%
class SimpleService(Service):
    def call(self, _: Context):
        logger.info(f"Service '{self.name}' is running...")


class NeverRunningService(Service):
    def call(self, _: Context):
        raise Exception(f"Oh no! The '{self.name}' service is running!")


class RuntimeInfoPrintingService(Service):
    def call(self, _: Context):
        logger.info(
            f"Service '{self.name}' runtime execution info:"
            f"{self.model_dump_json(self.info_dict, indent=4)}"
        )


# %%
pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "pre_services": [
        SimpleService,  # This simple service
        # will be named `SimpleService_0`
        SimpleService,  # This simple service
        # will be named `SimpleService_1`
    ],  # Despite this is the unnamed service group in the root
    # service group, it will be named `pre` as it holds pre services
    "post_services": [
        ServiceGroup(
            name="named_group",
            components=[
                Service(
                    handler=SimpleService,
                    start_condition=All(
                        ServiceFinishedCondition(
                            path=".pipeline.pre.SimpleService_0"
                        ),
                        ServiceFinishedCondition(
                            path=".pipeline.pre.SimpleService_1"
                        ),
                    ),  # Alternative:
                    # service_successful_condition(".pipeline.pre")
                    name="running_service",
                ),  # This simple service will be named `running_service`,
                # because its name is manually overridden
                Service(
                    handler=NeverRunningService,
                    start_condition=Not(
                        ServiceFinishedCondition(
                            path=".pipeline.post.named_group.SimpleService"
                        )
                    ),
                ),
            ],
            requested_async_flag=False,  # forbid services from running in async
        ),
        RuntimeInfoPrintingService,
    ],
}

# %%
pipeline = Pipeline.model_validate(pipeline_dict)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    check_happy_path(pipeline, HAPPY_PATH, printout=True)
    if is_interactive_mode():
        pipeline.run()
