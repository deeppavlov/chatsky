import asyncio

from chatsky import Context
from chatsky.utils.testing import TOY_SCRIPT

from chatsky.script import Message
from chatsky.pipeline import Pipeline, ServiceGroup
from chatsky.script.core.keywords import RESPONSE, TRANSITIONS
import chatsky.script.conditions as cnd


def test_script_getting_and_setting():
    script = {"old_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: {"": cnd.true()}}}}
    pipeline = Pipeline(script=script, start_label=("old_flow", ""))

    new_script = {"new_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: {"": cnd.false()}}}}
    pipeline.script = new_script
    pipeline.start_label = ("new_flow", "")
    assert list(pipeline.script.keys())[0] == list(new_script.keys())[0]


def test_parallel_services():
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

