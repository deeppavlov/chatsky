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
    def clean_ctx_misc(ctx: Context, __: Pipeline):
        ctx.current_node.misc = {"misc": []}

    def interact(stage: str):
        async def slow_service(ctx: Context, __: Pipeline):
            ctx.current_node.misc["misc"].append(stage)
            # This test is now about 0.3 seconds. Is that okay? We have lots of these tests.
            await asyncio.sleep(0.05)

        return slow_service

    def asserter_service(ctx: Context, __: Pipeline):
        assert ctx.current_node.misc["misc"] is ["A1", "B1", "A2", "B2", "A3", "B3", "C1", "C2", "C3"]
        # Checking if the test will fail from this. If it does, then the test is correct.
        assert False

    # Extracting Context like this, because I don't recall easier ways to access it.
    def context_extractor(result: list):
        async def inner(ctx: Context, __: Pipeline):
            result.append(ctx)
        return inner

    context = []
    pipeline_dict = {
        "script": TOY_SCRIPT,
        "start_label": ("greeting_flow", "start_node"),
        "fallback_label": ("greeting_flow", "fallback_node"),
        "pre_services": ServiceGroup(
            components=[clean_ctx_misc for _ in range(0, 10)],
            all_async=True,
        ),
        "post_services": [
            clean_ctx_misc,
            ServiceGroup(
                name="InteractWithServiceA",
                components=[
                    interact("A1"),
                    interact("A2"),
                    interact("A3"),
                ],
                asynchronous=True,
            ),
            ServiceGroup(
                name="InteractWithServiceB",
                components=[
                    interact("B1"),
                    interact("B2"),
                    interact("B3"),
                ],
                asynchronous=True,
            ),
            ServiceGroup(
                name="InteractWithServiceC",
                components=[
                    interact("C1"),
                    interact("C2"),
                    interact("C3"),
                ],
                asynchronous=False,
            ),
            asserter_service,
            context_extractor(context),
        ],
    }
    pipeline = Pipeline(**pipeline_dict)
    check_happy_path(pipeline, HAPPY_PATH)
    # Checking if 'asserter_service()' passed execution.
    # If everything is done correctly, this test should fail.
    assert pipeline._services_pipeline[-2].get_state(*context) is ComponentExecutionState.FINISHED
