import asyncio

from chatsky import Context
from chatsky.utils.testing import TOY_SCRIPT

from chatsky.script import Message
from chatsky.pipeline import Pipeline, ServiceGroup
from chatsky.pipeline.types import ComponentExecutionState
from chatsky.script.core.keywords import RESPONSE, TRANSITIONS
from chatsky.utils.testing.common import check_happy_path
from chatsky.utils.testing.toy_script import HAPPY_PATH
import chatsky.script.conditions as cnd


def test_script_getting_and_setting():
    script = {"old_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: {"": cnd.true()}}}}
    pipeline = Pipeline(script=script, start_label=("old_flow", ""))

    new_script = {"new_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: {"": cnd.false()}}}}
    pipeline.script = new_script
    pipeline.start_label = ("new_flow", "")
    assert list(pipeline.script.keys())[0] == list(new_script.keys())[0]


def test_parallel_services():
    def clean_run_order(run_order: list):
        async def inner(_: Context, __: Pipeline):
            run_order.clear()
        return inner

    def interact(stage: str, run_order: list):
        async def slow_service(ctx: Context, __: Pipeline):
            run_order.append(stage)
            # This test is now about 0.3 seconds. Is that okay? We have lots of these tests.
            await asyncio.sleep(0.05)

        return slow_service

    def asserter_service(run_order: list):
        async def inner(_: Context, __: Pipeline):
            assert run_order is ["A1", "B1", "A2", "B2", "A3", "B3", "C1", "C2", "C3"]
            # Checking if the test will fail from this. If it does, then the test is correct.
            assert False
        return inner

    # Extracting Context like this, because I don't recall easier ways to access it.
    def context_extractor(result: list):
        async def inner(ctx: Context, __: Pipeline):
            result.append(ctx)
        return inner

    running_order = []
    context = []
    pipeline_dict = {
        "script": TOY_SCRIPT,
        "start_label": ("greeting_flow", "start_node"),
        "fallback_label": ("greeting_flow", "fallback_node"),
        "post_services": [
            clean_run_order,
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
            asserter_service(running_order),
            context_extractor(context)
        ],
    }
    pipeline = Pipeline(**pipeline_dict)
    check_happy_path(pipeline, HAPPY_PATH)
    # Checking if 'asserter_service()' passed execution.
    # If everything is done correctly, this test should fail.
    assert pipeline._services_pipeline[-2].get_state(*context) is ComponentExecutionState.FINISHED
