# %% [markdown]
"""
# 5. Asynchronous groups and services (basic)

The following tutorial shows `pipeline` asynchronous
service and service group usage.

Here, %mddoclink(api,pipeline.service.group,ServiceGroup)s
are shown for advanced and asynchronous data pre- and postprocessing.
"""

# %pip install dff

# %%
import asyncio

from dff.pipeline import Pipeline, ACTOR

from dff.utils.testing.common import (
    is_interactive_mode,
    check_happy_path,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import HAPPY_PATH, TOY_SCRIPT

# %% [markdown]
"""
Services and service groups can be synchronous and asynchronous.
In synchronous service groups services are executed consequently.
In asynchronous service groups all services are executed simultaneously.

Service can be asynchronous if its handler is an async function.
Service group can be asynchronous if all services
and service groups inside it are asynchronous.

Here there is an asynchronous service group, that contains 10 services,
each of them should sleep for 0.01 of a second.
However, as the group is asynchronous,
it is being executed for 0.01 of a second in total.
Service group can be synchronous or asynchronous.
"""


# %%
async def time_consuming_service(_):
    await asyncio.sleep(0.01)


pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "components": [
        [time_consuming_service for _ in range(0, 10)],
        ACTOR,
    ],
}

# %%
pipeline = Pipeline.from_dict(pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
