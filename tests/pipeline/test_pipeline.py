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


def test_parallel_services():
    def interact(stage: str, run_order: list):
        async def slow_service(_: Context, __: Pipeline):
            run_order.append(stage)
            await asyncio.sleep(0)

        return slow_service

    running_order = []
    test_group = ServiceGroup(components=[
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
    )

    pipeline = Pipeline(script={}, start_label=("old_flow", ""))
    test_group(Context(), pipeline)
    assert running_order == ["A1", "B1", "A2", "B2", "A3", "B3", "C1", "C2", "C3"]
