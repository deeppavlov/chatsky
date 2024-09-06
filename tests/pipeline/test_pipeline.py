import asyncio

from chatsky.core import Context, Pipeline
from chatsky.core.service import ServiceGroup

from chatsky.utils.testing import TOY_SCRIPT


def test_async_services():
    def interact(stage: str, run_order: list):
        async def slow_service(_: Context):
            run_order.append(stage)
            await asyncio.sleep(0)
            print("Hi or something.")

        return slow_service

    running_order = []
    test_group = ServiceGroup(
        components=[
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

    ctx = Context.init(("greeting_flow", "start_node"))
    pipeline = Pipeline(pre_services=test_group, script=TOY_SCRIPT, start_label=("greeting_flow", "start_node"))
    asyncio.run(pipeline.pre_services(ctx))
    assert running_order == ["A1", "B1", "A2", "B2", "A3", "B3", "C1", "C2", "C3"]
