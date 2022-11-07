"""
Groups and conditions (basic)
=============================

The following example shows pipeline service group usage and start conditions
"""

import json
import logging

from dff.core.pipeline import Service, Pipeline, not_condition, service_successful_condition, ServiceRuntimeInfo
from dff.utils.common import create_example_actor, run_example

logger = logging.getLogger(__name__)

"""
Pipeline can contain not only single services, but also service groups.
Service groups can be defined as ServiceGroupBuilder objects:
      lists of ServiceBuilders and ServiceGroupBuilders or objects.
The objects should contain `services` - a ServiceBuilder and ServiceGroupBuilder object list.

To receive serialized information about service, service group or pipeline a property `info_dict` can be used,
      it returns important object properties as a dict.

Services and service groups can be executed conditionally.
Conditions are functions passed to `start_condition` argument.
These functions should have following signature: (ctx: Context, actor: Actor) -> bool.
Service is only executed if its start_condition returned True.
By default all the services start unconditionally. There are number of built-in condition functions.
Built-in condition functions check other service states. These are most important built-in condition functions:
    `always_start_condition` - default condition function, always starts service
    `service_successful_condition(path)` - function that checks,
                                           whether service with given `path` executed successfully
    `not_condition(function)` - function that returns result opposite from the one returned
                                by the `function` (condition function) argument

Here there is a conditionally executed service named `never_running_service` is always executed.
It is executed only if `always_running_service` is not finished, this should never happen.
The service, named `context_printing_service` prints pipeline runtime information,
that contains execution state of all previously run services.
"""


def always_running_service(_, __, info: ServiceRuntimeInfo):
    logger.info(f"Service '{info['name']}' is running...")


def never_running_service(_, __, info: ServiceRuntimeInfo):
    raise Exception(f"Oh no! The '{info['name']}' service is running!")


def runtime_info_printing_service(_, __, info: ServiceRuntimeInfo):
    logger.info(f"Service '{info['name']}' runtime execution info: {json.dumps(info, indent=4, default=str)}")


pipeline_dict = {
    "components": [
        Service(
            handler=always_running_service,
            name="always_running_service",
        ),
        create_example_actor(),
        Service(
            handler=never_running_service,
            start_condition=not_condition(service_successful_condition(".pipeline.always_running_service")),
        ),
        Service(
            handler=runtime_info_printing_service,
            name="runtime_info_printing_service",
        ),
    ],
}


pipeline = Pipeline.from_dict(pipeline_dict)

if __name__ == "__main__":
    run_example(logger, pipeline=pipeline)
