import asyncio

import pytest

from chatsky.core import Context, Pipeline
from chatsky.core.service import ServiceGroup, Service, ComponentExecutionState
from chatsky.core.service.extra import ComponentExtraHandler
from chatsky.core.utils import initialize_service_states

from chatsky.utils.testing import TOY_SCRIPT


@pytest.fixture()
def make_test_service_group():
    def inner(running_order: list) -> ServiceGroup:
        def interact(stage: str, run_order: list):
            async def slow_service(_: Context):
                run_order.append(stage)
                await asyncio.sleep(0)

            return slow_service

        test_group = ServiceGroup(
            components=[
                ServiceGroup(
                    name="InteractWithServiceA",
                    components=[
                        interact("A1", running_order),
                        interact("A2", running_order),
                        interact("A3", running_order),
                    ],
                ),
                ServiceGroup(
                    name="InteractWithServiceB",
                    components=[
                        interact("B1", running_order),
                        interact("B2", running_order),
                        interact("B3", running_order),
                    ],
                ),
                ServiceGroup(
                    name="InteractWithServiceC",
                    components=[
                        interact("C1", running_order),
                        interact("C2", running_order),
                        interact("C3", running_order),
                    ],
                ),
            ],
        )
        return test_group
    return inner


@pytest.fixture()
def run_test_group(context_factory):
    async def inner(test_group: ServiceGroup) -> ComponentExecutionState:
        ctx = context_factory(start_label=("greeting_flow", "start_node"))
        pipeline = Pipeline(pre_services=test_group, script=TOY_SCRIPT, start_label=("greeting_flow", "start_node"))
        initialize_service_states(ctx, pipeline.pre_services)
        await pipeline.pre_services(ctx)
        return test_group.get_state(ctx)
    return inner

@pytest.fixture()
def run_extra_handler(context_factory):
    async def inner(extra_handler: ComponentExtraHandler) -> ComponentExecutionState:
        ctx = context_factory(start_label=("greeting_flow", "start_node"))
        service = Service(handler=lambda _: None, before_handler=extra_handler)
        initialize_service_states(ctx, service)
        await service(ctx)
        return service.get_state(ctx)
    return inner
