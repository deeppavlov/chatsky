import asyncio

from chatsky import Context
from chatsky.utils.testing import TOY_SCRIPT

from chatsky.core import Pipeline, Message, RESPONSE, TRANSITIONS, Transition as Tr
from chatsky.core.service import ServiceGroup
from chatsky.utils.testing.common import check_happy_path
from chatsky.utils.testing.toy_script import HAPPY_PATH


def test_script_getting_and_setting():
    script = {"old_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: [Tr(dst="", cnd=True)]}}}
    pipeline = Pipeline(script=script, start_label=("old_flow", ""))

    new_script = {"new_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: [Tr(dst="", cnd=False)]}}}
    pipeline.script = new_script
    pipeline.start_label = ("new_flow", "")
    assert list(pipeline.script.keys())[0] == list(new_script.keys())[0]


def test_parallel_services():
    def interact(stage: str, run_order: list):
        async def slow_service(_: Context, __: Pipeline):
            run_order.append(stage)
            # This test is now about 1.5 seconds. Is that really okay? We have lots of these tests.
            await asyncio.sleep(0.05)

        return slow_service

    running_order = []
    pipeline_dict = {
        "script": TOY_SCRIPT,
        "start_label": ("greeting_flow", "start_node"),
        "fallback_label": ("greeting_flow", "fallback_node"),
        "post_services": [
            ServiceGroup(
                name="InteractWithServiceA",
                components=[
                    interact("A1", running_order),
                    interact("A2", running_order),
                    interact("A3", running_order),
                ],
                asynchronous=True,
            ),
            ServiceGroup(
                name="InteractWithServiceB",
                components=[
                    interact("B1", running_order),
                    interact("B2", running_order),
                    interact("B3", running_order),
                ],
                asynchronous=True,
            ),
            ServiceGroup(
                name="InteractWithServiceC",
                components=[
                    interact("C1", running_order),
                    interact("C2", running_order),
                    interact("C3", running_order),
                ],
                asynchronous=False,
            ),
        ],
    }
    pipeline = Pipeline(**pipeline_dict)
    check_happy_path(pipeline, HAPPY_PATH)
    # Since there are 5 requests in the 'HAPPY_PATH', multiplying the running order by 5.
    assert running_order == ["A1", "B1", "A2", "B2", "A3", "B3", "C1", "C2", "C3"] * 5
