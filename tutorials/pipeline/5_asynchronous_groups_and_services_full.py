# %% [markdown]
"""
# 5. Asynchronous groups and services (full)

The following tutorial shows `pipeline`
asynchronous service and service group usage.

This tutorial is a more advanced version of the
[previous tutorial](
%doclink(tutorial,pipeline.5_asynchronous_groups_and_services_basic)
).
"""

# %pip install dff

# %%
import asyncio
import json
import logging
import urllib.request

from dff.script import Context

from dff.pipeline import ServiceGroup, Pipeline, ServiceRuntimeInfo, ACTOR

from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import HAPPY_PATH, TOY_SCRIPT

logger = logging.getLogger(__name__)

# %% [markdown]
"""
Services and service groups can be synchronous and asynchronous.
In synchronous service groups services are executed consequently,
    some of them (`ACTOR`) can even return `Context` object,
    modifying it.
In asynchronous service groups all services
    are executed simultaneously and should not return anything,
    neither modify Context.

To become asynchronous service or service group
    should _be able_ to be asynchronous
    and should not be marked synchronous.
Service can be asynchronous if its handler is an async function.
Service group can be asynchronous if all services
and service groups inside it are asynchronous.
If service or service group can be asynchronous
the `asynchronous` constructor parameter is checked.
If the parameter is not set,
the service becomes asynchronous, and if set, it is used instead.
If service can not be asynchronous,
but is marked asynchronous, an exception is thrown.
ACTOR service is asynchronous.

The timeout field only works for asynchronous services and service groups.
If service execution takes more time than timeout,
it is aborted and marked as failed.

Pipeline `optimization_warnings` argument can be used to
    display optimization warnings during pipeline construction.
Generally for optimization purposes asynchronous
    services should be combined into asynchronous
    groups to run simultaneously.
Synchronous services should be expelled from (mostly) asynchronous groups.

Here service group `balanced_group` can be asynchronous,
    however it is requested to be synchronous,
    so its services are executed consequently.
Service group `service_group_0` is asynchronous,
    it doesn't run out of timeout of 0.02 seconds,
    however contains 6 time consuming services,
    each of them sleeps for 0.01 of a second.
Service group `service_group_1` is also asynchronous,
it logs HTTPS requests (from 1 to 15),
    running simultaneously, in random order.
Service group `pipeline` can't be asynchronous because
`balanced_group` and ACTOR are synchronous.
"""


# %%
async def simple_asynchronous_service(_, __, info: ServiceRuntimeInfo):
    logger.info(f"Service '{info.name}' is running")


async def time_consuming_service(_):
    await asyncio.sleep(0.01)


def meta_web_querying_service(
    photo_number: int,
):  # This function returns services, a service factory
    async def web_querying_service(ctx: Context, _, info: ServiceRuntimeInfo):
        if ctx.misc.get("web_query", None) is None:
            ctx.misc["web_query"] = {}
        with urllib.request.urlopen(
            f"https://jsonplaceholder.typicode.com/photos/{photo_number}"
        ) as webpage:
            web_content = webpage.read().decode(
                webpage.headers.get_content_charset()
            )
            ctx.misc["web_query"].update(
                {
                    f"{ctx.last_request}"
                    f":photo_number_{photo_number}": json.loads(web_content)[
                        "title"
                    ]
                }
            )
        logger.info(f"Service '{info.name}' has completed HTTPS request")

    return web_querying_service


def context_printing_service(ctx: Context):
    logger.info(f"Context misc: {json.dumps(ctx.misc, indent=4, default=str)}")


# %%
pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "optimization_warnings": True,
    # There are no warnings - pipeline is well-optimized
    "components": [
        ServiceGroup(
            name="balanced_group",
            asynchronous=False,
            components=[
                simple_asynchronous_service,
                ServiceGroup(
                    timeout=0.02,
                    components=[time_consuming_service for _ in range(0, 6)],
                ),
                simple_asynchronous_service,
            ],
        ),
        ACTOR,
        [meta_web_querying_service(photo) for photo in range(1, 16)],
        context_printing_service,
    ],
}

# %%
pipeline = Pipeline.from_dict(pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
