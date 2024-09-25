import asyncio
from typing import Any

import pytest

from chatsky import Context, BaseProcessing, Pipeline, Message
from chatsky.conditions import ServiceFinished
from chatsky.core.service import (
    Service,
    ServiceGroup,
    ComponentExecutionState,
    GlobalExtraHandlerType,
    ExtraHandlerRuntimeInfo,
)
from chatsky.core.service.extra import BeforeHandler
from chatsky.core.utils import initialize_service_states
from chatsky.utils.testing import TOY_SCRIPT
from .utils import run_test_group, make_test_service_group, run_extra_handler


@pytest.fixture
def empty_context():
    return Context.init(("", ""))


async def test_pipeline_component_order(empty_context):
    logs = []

    class MyProcessing(BaseProcessing):
        wait: float
        text: str

        async def call(self, ctx: Context):
            await asyncio.sleep(self.wait)
            logs.append(self.text)

    script = {"": {"": {"pre_response": {"": MyProcessing(wait=0.01, text="B")}}}}
    pipeline = Pipeline(
        script,
        ("", ""),
        pre_services=[MyProcessing(wait=0.02, text="A")],
        post_services=[MyProcessing(wait=0, text="C")],
    )
    initialize_service_states(empty_context, pipeline.services_pipeline)
    await pipeline._run_pipeline(Message(""), empty_context.id)
    assert logs == ["A", "B", "C"]


def test_async_services():
    running_order = []
    test_group = make_test_service_group(running_order)
    test_group.components[0].asynchronous = True
    test_group.components[1].asynchronous = True

    run_test_group(test_group)
    assert running_order == ["A1", "B1", "A2", "B2", "A3", "B3", "C1", "C2", "C3"]


def test_all_async_flag():
    running_order = []
    test_group = make_test_service_group(running_order)
    test_group.all_async = True

    run_test_group(test_group)
    assert running_order == ["A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"]


def test_extra_handler_timeouts():
    def bad_function(timeout: float, bad_func_completed: list):
        def inner(_: Context, __: ExtraHandlerRuntimeInfo) -> None:
            asyncio.run(asyncio.sleep(timeout))
            bad_func_completed.append(True)

        return inner

    # Timeout expires before the exception is raised, which is then logged.
    test_list = []
    extra_handler = BeforeHandler(functions=bad_function(1.0, test_list), timeout=0.0, asynchronous=True)
    run_extra_handler(extra_handler)
    assert test_list == []

    # This is here just to demonstrate that the timeout is working.
    extra_handler = BeforeHandler(functions=bad_function(0.0, test_list), timeout=1.0, asynchronous=True)
    run_extra_handler(extra_handler)
    assert test_list == [True]


def test_extra_handler_function_signatures():
    def one_parameter_func(_: Context) -> None:
        pass

    def two_parameter_func(_: Context, __: ExtraHandlerRuntimeInfo) -> None:
        pass

    def three_parameter_func(_: Context, __: ExtraHandlerRuntimeInfo, ___: Any) -> None:
        pass

    def no_parameters_func() -> None:
        pass

    assert run_extra_handler(one_parameter_func) == ComponentExecutionState.FINISHED
    assert run_extra_handler(two_parameter_func) == ComponentExecutionState.FINISHED

    assert run_extra_handler(three_parameter_func) == ComponentExecutionState.FAILED
    assert run_extra_handler(no_parameters_func) == ComponentExecutionState.FAILED


# Checking that async functions can be run as extra_handlers.
def test_async_extra_handler_func():
    def append_list(record: list):
        async def async_func(_: Context, __: ExtraHandlerRuntimeInfo):
            record.append("Value")

        return async_func

    test_list = []
    extra_handler = BeforeHandler(functions=append_list(test_list), asynchronous=True)
    run_extra_handler(extra_handler)
    assert test_list == ["Value"]


def test_service_computed_names():
    def normal_func(_: Context) -> None:
        pass

    service = Service(handler=normal_func)
    assert service.computed_name == "normal_func"

    class MyService(Service):
        async def call(self, ctx: Context):
            pass

    service = MyService()
    assert service.computed_name == "MyService"

    class MyProcessing(BaseProcessing):
        async def call(self, ctx: Context):
            pass

    func_class = MyProcessing()
    service = Service(handler=func_class)
    assert service.computed_name == "MyProcessing"


# 'all_async' flag will try to run all services simultaneously, but the 'wait' option
# makes it so that A waits for B, which waits for C. So "C" is first, "A" is last.
def test_waiting_for_service_to_finish_condition():
    running_order = []
    test_group = make_test_service_group(running_order)
    test_group.all_async = True
    test_group.components[0].start_condition = ServiceFinished(".pipeline.pre.InteractWithServiceB", wait=True)
    test_group.components[1].start_condition = ServiceFinished(".pipeline.pre.InteractWithServiceC", wait=True)

    run_test_group(test_group)
    assert running_order == ["C1", "C2", "C3", "B1", "B2", "B3", "A1", "A2", "A3"]


def test_bad_service():
    def bad_service_func(_: Context) -> None:
        raise Exception("Custom exception")

    test_group = ServiceGroup.model_validate([bad_service_func])
    assert run_test_group(test_group) == ComponentExecutionState.FAILED


async def test_service_not_run(empty_context):
    service = Service(handler=lambda ctx: None, start_condition=False)
    initialize_service_states(empty_context, service)
    await service(empty_context)
    assert service.get_state(empty_context) == ComponentExecutionState.NOT_RUN


def test_inherited_extra_handlers_for_service_groups_with_conditions():
    def extra_handler_func(counter: list):
        def inner(_: Context) -> None:
            counter.append("Value")

        return inner

    def condition_func(path: str):
        if path == ".pipeline.pre.InteractWithServiceA" or path == ".pipeline.pre.service":
            return True
        return False

    counter_list = []
    test_group = make_test_service_group(list())

    service = Service(handler=lambda _: None, name="service")
    test_group.components.append(service)

    ctx = Context.init(("greeting_flow", "start_node"))
    pipeline = Pipeline(pre_services=test_group, script=TOY_SCRIPT, start_label=("greeting_flow", "start_node"))

    test_group.add_extra_handler(GlobalExtraHandlerType.BEFORE, extra_handler_func(counter_list), condition_func)
    initialize_service_states(ctx, test_group)

    asyncio.run(pipeline.pre_services(ctx))
    # One for original ServiceGroup, one for each of the defined paths in the condition function.
    assert counter_list == ["Value"] * 3
