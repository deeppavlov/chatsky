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

# %pip install chatsky

# %%
import asyncio
import json
import logging
import urllib.request

from chatsky.pipeline import (
    ServiceGroup,
    Pipeline,
    ServiceRuntimeInfo,
    to_service,
)
from chatsky.script import Context
from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from chatsky.utils.testing.toy_script import HAPPY_PATH, TOY_SCRIPT

logger = logging.getLogger(__name__)

# %% [markdown]
"""
Services and service groups are `PipelineComponent`s,
which can be synchronous or asynchronous.
All `ServiceGroup`s are made of these `PipelineComponent`s.

Synchronous components are executed consequently,
    some of them can even return `Context` object,
    modifying it.
Asynchronous components are executed
    simultaneously and should not return anything,
    neither modify `Context`.
The main reason all services can't be asynchronous is because there
are services which can modify the `Context`.

It should be noted that only adjacent asynchronous components in a
`ServiceGroup` are executed simultaneously, unless overridden
with 'all_async' flag, then all components are considered asynchronous.
To put it bluntly, [a, s, a, a, a, s] -> a, s, (a, a, a), s,
those three adjacent async functions will run simultaneously.
Basically, the order of your services in the list matters.

The timeout field only works for asynchronous services and service groups.
If service execution takes more time than timeout,
it is aborted and marked as failed.

Pipeline `optimization_warnings` argument can be used to
    display optimization warnings during pipeline construction.
Generally for optimization purposes asynchronous
    services should not be contained in nested or different ServiceGroups.
    (different ServiceGroups that aren't marked as 'asynchronous' themselves)
    Instead, it's best to keep all asynchronous components inside the same
    ServiceGroup, so that the program can easily keep track of them
    and guarantee optimized performance.
Synchronous services should be expelled from (mostly) asynchronous groups.

Here service group `balanced_group` could be fully asynchronous,
    however it is not requested, so the group will be synchronous,
    meaning its services are executed with default
    `ServiceGroup` execution logic.
Service group `service_group_0` is not marked as 'asynchronous',
    meaning 'balanced_group' treats it as a synchronous component,
    waiting for the previous component to finish before running this one.
`service_group_0` only has async components inside, so
    it doesn't run out of timeout of 0.02 seconds,
    even though it contains 6 time consuming services,
    each of them sleeping for 0.01 of a second.
Service group `service_group_1` is also asynchronous,
it logs HTTPS requests (from 1 to 15),
    running simultaneously, in random order.
Service group `pipeline` can't be asynchronous because
`balanced_group` and `Actor` are synchronous.
(`Actor` is added into `Pipeline`'s 'components' during it's creation)
"""


# %%
@to_service(asynchronous=True)
async def simple_asynchronous_service(_, __, info: ServiceRuntimeInfo):
    logger.info(f"Service '{info.name}' is running")


@to_service(asynchronous=True)
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
    "pre_services": ServiceGroup(
        name="balanced_group",
        components=[
            simple_asynchronous_service,
            ServiceGroup(
                name="service_group_0",
                timeout=0.02,
                components=[time_consuming_service for _ in range(0, 6)],
            ),
            simple_asynchronous_service,
        ],
    ),
    "post_services": [
        ServiceGroup(
            name="service_group_1",
            components=[
                [meta_web_querying_service(photo) for photo in range(1, 16)],
                context_printing_service,
            ],
            all_async=True
        )
    ],
}

# %%
pipeline = Pipeline.model_validate(pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
