# %% [markdown]
"""
# 5. Asynchronous groups and services

The following tutorial shows `pipeline` asynchronous
service and service group usage.

Here, %mddoclink(api,core.service.group,ServiceGroup)s
are shown for advanced and asynchronous data pre- and postprocessing.
"""

# %pip install chatsky

# %%
import asyncio
import logging
import sys
from importlib import reload

from chatsky.core import Context, Pipeline
from chatsky.core.service import ServiceGroup

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
Services and service groups are `PipelineComponent`s,
which can be synchronous or asynchronous.
All `ServiceGroup`s are made of these `PipelineComponent`s.

Synchronous components are executed sequentially, while
asynchronous components work simultaneously.
By default, all `PipelineComponent`s are synchronous,
but can be marked as 'asynchronous'.

It should be noted that only adjacent asynchronous components in a
`ServiceGroup` are executed simultaneously.
To put it bluntly, if "s" means sync component and "a" means async,
then [a, s, a, a, a, s] -> a, s, (a, a, a), s.
Those three adjacent async components will run simultaneously.
Basically, the order of your services in the list is crucial.

Service groups have a flag 'all_async' which makes it treat
every component inside it as asynchronous,
running all components simultaneously. (by default it's `False`)
This is convenient if you have a bunch of functions,
that you want to run simultaneously,
but don't want to make a service for each of them.

In this example, there's a service group named "pre_services" with the
`all_async` flag set to `True`, containing 10 services, each of which sleeps
for 0.01 seconds. Since the group is fully asynchronous, the total execution
time is just 0.01 seconds. The same would apply if all those services were
marked as `asynchronous`. By default, if services are not explicitly marked as
asynchronous, they will execute sequentially.

To further demonstrate ServiceGroup's logic,
"post_services" is a ServiceGroup with asynchronous components 'A' and 'B',
which execute simultaneously, and also one non-async component 'C' at the end.
If 'A' and 'B' weren't async, all steps for component 'A' would complete
before component 'B' begins its execution, but instead they start
at the same time. Only after both of them have finished,
does component 'C' start working.
"""


# %%
async def time_consuming_service(_):
    await asyncio.sleep(0.01)


def interact(stage: str, service: str):
    async def slow_service(_: Context):
        logger.info(f"{stage} with service {service}")
        await asyncio.sleep(0.1)

    return slow_service


pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "pre_services": ServiceGroup(
        components=[time_consuming_service for _ in range(0, 10)],
        all_async=True,
    ),
    "post_services": [
        ServiceGroup(
            name="InteractWithServiceA",
            components=[
                interact("Starting interaction", "A"),
                interact("Finishing interaction", "A"),
            ],
            asynchronous=True,
        ),
        ServiceGroup(
            name="InteractWithServiceB",
            components=[
                interact("Starting interaction", "B"),
                interact("Finishing interaction", "B"),
            ],
            asynchronous=True,
        ),
        ServiceGroup(
            name="InteractWithServiceC",
            components=[
                interact("Starting interaction", "C"),
                interact("Finishing interaction", "C"),
            ],
            asynchronous=False,
        ),
    ],
}

# %%
pipeline = Pipeline.model_validate(pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH, printout=True)
    if is_interactive_mode():
        pipeline.run()
