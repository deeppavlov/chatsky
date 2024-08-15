# %% [markdown]
"""
# 5. Asynchronous groups and services

The following tutorial shows `pipeline` asynchronous
service and service group usage.

Here, %mddoclink(api,pipeline.service.group,ServiceGroup)s
are shown for advanced and asynchronous data pre- and postprocessing.
"""

# %pip install chatsky

# %%
import asyncio

from chatsky import Context
from chatsky.pipeline import Pipeline, ServiceGroup

from chatsky.utils.testing.common import (
    is_interactive_mode,
    check_happy_path,
    run_interactive_mode,
)
from chatsky.utils.testing.toy_script import HAPPY_PATH, TOY_SCRIPT

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
By default, all `PipelineComponent`s are synchronous,
but can be marked as 'asynchronous'.

It should be noted that only adjacent asynchronous components in a
`ServiceGroup` are executed simultaneously.
To put it bluntly, [a, s, a, a, a, s] -> a, s, (a, a, a), s,
those three adjacent async functions will run simultaneously.
Basically, the order of your services in the list matters.

Service groups have a flag 'all_async' which makes it treat
every component inside it as asynchronous,
running all components simultaneously. (by default it's `False`)
This is convenient if you have a bunch of functions,
that you want to run simultaneously,
but don't want to make a service for each of them.

Here, "pre_services" is a service group with the flag
'all_async' set to 'True', that contains 10 services,
each of them should sleep for 0.01 of a second.
However, as the group is fully asynchronous,
it is being executed for 0.01 of a second in total.
The same would happen if all of those services were marked as 'asynchronous'.
Once again, by default, all services inside a
service group are executed sequentially if they
weren't explicitly marked as asynchronous.

To further demonstrate ServiceGroup's logic,
"post_services" is a ServiceGroup with asynchronous components 'A' and 'B',
which execute simultaneously, and also one non-async component 'C' at the end.
If 'A' and 'B' weren't async, then all steps for component 'A'
would pass first and only then would execution start for
component 'B', but instead they start
at the same time. Only after both of them have finished,
does component 'C' start working.
"""


# %%
async def time_consuming_service(_):
    await asyncio.sleep(0.01)


def interact(stage: str, service: str):
    async def slow_service(_: Context, __: Pipeline):
        print(f"{stage} with service {service}")
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
                interact("Interacting", "A"),
                interact("Finishing interaction", "A"),
            ],
            asynchronous=True,
        ),
        ServiceGroup(
            name="InteractWithServiceB",
            components=[
                interact("Starting interaction", "B"),
                interact("Interacting", "B"),
                interact("Finishing interaction", "B"),
            ],
            asynchronous=True,
        ),
        ServiceGroup(
            name="InteractWithServiceC",
            components=[
                interact("Starting interaction", "C"),
                interact("Interacting", "C"),
                interact("Finishing interaction", "C"),
            ],
            asynchronous=False,
        ),
    ],
}

# %%
pipeline = Pipeline.model_validate(pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
