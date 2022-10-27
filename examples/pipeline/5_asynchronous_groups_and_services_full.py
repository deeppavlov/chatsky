"""
Asynchronous groups and services (full)
=======================================

The following example shows pipeline asynchronous service and service group usage
"""

import asyncio
import json
import logging
import urllib.request

from dff.core.engine.core import Actor, Context

from dff.core.pipeline import ServiceGroup, Pipeline, ServiceRuntimeInfo
from examples.pipeline._pipeline_utils import SCRIPT, get_auto_arg, auto_run_pipeline

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

"""
Services and service groups can be synchronous and asynchronous.
In synchronous service groups services are executed consequently, some of them (actor) can even return Context object, modifying it.
In asynchronous service groups all services are executed simultaneously and should not return anything, neither modify Context.

To become asynchronous service or service group should _be able_ to be asynchronous and should not be marked synchronous.
Service can be asynchronous if its handler is an async function.
Service group can be asynchronous if all services and service groups inside it are asynchronous.
If service or service group can be asynchronous the `asynchronous` constructor parameter is checked.
If the parameter is not set, the service becomes asynchronous, if it is, it is used instead.
If service can not be asynchronous, but is marked asynchronous, an exception is thrown.
NB! Actor service is always synchronous.

The timeout field only works for asynchronous services and service groups.
If service execution takes more time than timeout, it is aborted and marked as failed.

Pipeline `optimization_warnings` argument can be used to display optimization warnings during pipeline construction.
Generally for optimization purposes asynchronous services should be combined into asynchronous groups to run simultaneously.
Synchronous services should be expelled from (mostly) asynchronous groups.

Here service group `balanced_group` can be asynchronous, however it is requested to be synchronous, so its services are executed consequently.
Service group `service_group_0` is asynchronous, it doesn't run out of timeout of 2 seconds, however contains 6 time consuming services, each of them sleeps for a second.
Service group `service_group_1` is also asynchronous, it logs HTTPS requests (from 1 to 15), running simultaneously, in random order.
Service group `pipeline` can't be asynchronous because `balanced_group` and actor are synchronous.
"""


actor = Actor(
    SCRIPT,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)


async def simple_asynchronous_service(_, __, info: ServiceRuntimeInfo):
    logger.info(f"Service '{info['name']}' is running")


async def time_consuming_service(_):
    await asyncio.sleep(1)


def meta_web_querying_service(photo_number: int):  # This function returns services, a service factory
    async def web_querying_service(ctx: Context, _, info: ServiceRuntimeInfo):
        if ctx.misc.get(f"web_query", None) is None:
            ctx.misc[f"web_query"] = {}
        with urllib.request.urlopen(f"https://jsonplaceholder.typicode.com/photos/{photo_number}") as webpage:
            web_content = webpage.read().decode(webpage.headers.get_content_charset())
            ctx.misc[f"web_query"].update(
                {f"{ctx.last_request}:photo_number_{photo_number}": json.loads(web_content)["title"]}
            )
        logger.info(f"Service '{info['name']}' has completed HTTPS request")

    return web_querying_service


def context_printing_service(ctx: Context):
    logger.info(f"Context misc: {json.dumps(ctx.misc, indent=4, default=str)}")


pipeline_dict = {
    "optimization_warnings": True,  # There are no warnings - pipeline is well-optimized
    "components": [
        ServiceGroup(
            name="balanced_group",
            asynchronous=False,
            components=[
                simple_asynchronous_service,
                ServiceGroup(timeout=2, components=[time_consuming_service for _ in range(0, 6)]),
                simple_asynchronous_service,
            ],
        ),
        actor,
        [meta_web_querying_service(photo) for photo in range(1, 16)],
        context_printing_service,
    ],
}


pipeline = Pipeline.from_dict(pipeline_dict)

if __name__ == "__main__":
    if get_auto_arg():
        auto_run_pipeline(pipeline, logger=logger)
    else:
        pipeline.run()
