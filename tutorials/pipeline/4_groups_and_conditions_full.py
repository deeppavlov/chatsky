# %% [markdown]
"""
# 4. Groups and conditions (full)

The following tutorial shows `pipeline`
service group usage and start conditions.

This tutorial is a more advanced version of the
[previous tutorial](%doclink(tutorial,pipeline.4_groups_and_conditions_basic)).
"""

# %pip install dff

# %%
import logging

from dff.pipeline import (
    Service,
    Pipeline,
    ServiceGroup,
    not_condition,
    service_successful_condition,
    all_condition,
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
Pipeline can contain not only single services, but also service groups.
Service groups can be defined as lists of `ServiceBuilders`
    (in fact, all of the pipeline services are combined
    into root service group named "pipeline").
Alternatively, the groups can be defined as objects
    with following constructor arguments:

* `components` (required) - A list of ServiceBuilder objects,
    ServiceGroup objects and lists of them.
* `wrappers` - A list of pipeline wrappers, see tutorial 7.
* `timeout` - Pipeline timeout, see tutorial 5.
* `asynchronous` - Whether or not this service group _should_ be asynchronous
    (keep in mind that not all service groups _can_ be asynchronous),
    see tutorial 5.
* `start_condition` - Service group start condition.
* `name` - Custom defined name for the service group
    (keep in mind that names in one ServiceGroup should be unique).

Service (and service group) object fields
are mostly the same as constructor parameters,
however there are some differences:

* `requested_async_flag` - Contains the value received
    from `asynchronous` constructor parameter.
* `calculated_async_flag` - Contains automatically calculated
    possibility of the service to be asynchronous.
* `asynchronous` - Combination af `..._async_flag` fields,
    requested value overrides calculated (if not `None`),
    see tutorial 5.
* `path` - Contains globally unique (for pipeline)
    path to the service or service group.

If no name is specified for a service or service group,
    the name will be generated according to the following rules:

1. If service's handler is an Actor, service will be named 'actor'.
2. If service's handler is callable,
    service will be named callable.
3. Service group will be named 'service_group'.
4. Otherwise, it will be named 'noname_service'.
5. After that an index will be added to service name.

To receive serialized information about service, service group
or pipeline a property `info_dict` can be used,
it returns important object properties as a dict.
In addition to that `pretty_format` method of Pipeline
can be used to get all pipeline properties as a formatted string
(e.g. for logging or debugging purposes).

Services and service groups can be executed conditionally.
Conditions are functions passed to `start_condition` argument.
These functions should have following signature:

    (ctx: Context, pipeline: Pipeline) -> bool.

Service is only executed if its start_condition returned `True`.
By default all the services start unconditionally.
There are number of built-in condition functions as well
as possibility to create custom ones.
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

There are following built-in condition functions:

* `always_start_condition` - Default condition function,
    always starts service.
* `service_successful_condition(path)` -
    Function that checks, whether service
    with given `path` executed successfully (is `FINISHED`).
* `not_condition(function)` -
    Function that returns result opposite
    from the one returned by
    the `function` (condition function) argument.
* `aggregate_condition(aggregator, *functions)` -
    Function that aggregated results of
    numerous `functions` (condition functions)
    using special `aggregator` function.
* `all_condition(*functions)` -
    Function that returns True only if all
    of the given `functions`
    (condition functions) return `True`.
* `any_condition(*functions)` -
    Function that returns `True`
    if any of the given `functions`
    (condition functions) return `True`.
NB! Actor service ALWAYS runs unconditionally.

Here there are two conditionally executed services:
a service named `running_service` is executed
    only if both `simple_services` in `service_group_0`
    are finished successfully.
`never_running_service` is executed only if `running_service` is not finished,
this should never happen.
`context_printing_service` prints pipeline runtime information,
    that contains execution state of all previously run services.
"""


# %%
def simple_service(_, __, info: ServiceRuntimeInfo):
    logger.info(f"Service '{info.name}' is running...")


def never_running_service(_, __, info: ServiceRuntimeInfo):
    raise Exception(f"Oh no! The '{info.name}' service is running!")


def runtime_info_printing_service(_, __, info: ServiceRuntimeInfo):
    logger.info(
        f"Service '{info.name}' runtime execution info:"
        f"{info.model_dump_json(indent=4, default=str)}"
    )


# %%
pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "components": [
        [
            simple_service,  # This simple service
            # will be named `simple_service_0`
            simple_service,  # This simple service
            # will be named `simple_service_1`
        ],  # Despite this is the unnamed service group in the root
        # service group, it will be named `service_group_0`
        ACTOR,
        ServiceGroup(
            name="named_group",
            components=[
                Service(
                    handler=simple_service,
                    start_condition=all_condition(
                        service_successful_condition(
                            ".pipeline.service_group_0.simple_service_0"
                        ),
                        service_successful_condition(
                            ".pipeline.service_group_0.simple_service_1"
                        ),
                    ),  # Alternative:
                    # service_successful_condition(".pipeline.service_group_0")
                    name="running_service",
                ),  # This simple service will be named `running_service`,
                # because its name is manually overridden
                Service(
                    handler=never_running_service,
                    start_condition=not_condition(
                        service_successful_condition(
                            ".pipeline.named_group.running_service"
                        )
                    ),
                ),
            ],
        ),
        runtime_info_printing_service,
    ],
}

# %%
pipeline = Pipeline.from_dict(pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        logger.info(f"Pipeline structure:\n{pipeline.pretty_format()}")
        run_interactive_mode(pipeline)
