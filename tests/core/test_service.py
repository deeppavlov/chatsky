import asyncio
import pytest

from chatsky import Context, BaseProcessing
from chatsky.core.service import Service, ServiceGroup, ComponentExecutionState
from chatsky.core.service.extra import BeforeHandler
from .utils import run_test_group, make_test_service_group, run_extra_handler


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
        def inner(_, __) -> None:
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
    def one_parameter_func(ctx: Context) -> None:
        pass

    def two_parameter_func(_, __) -> None:
        pass

    def three_parameter_func(_, __, ___) -> None:
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
        async def async_func(_, __):
            record.append("Value")

        return async_func

    test_list = []
    extra_handler = BeforeHandler(functions=append_list(test_list), asynchronous=True)
    run_extra_handler(extra_handler)
    assert test_list == ["Value"]


def test_service_computed_names():
    def normal_func(ctx: Context) -> None:
        pass

    service = Service(handler=normal_func)
    assert service.computed_name == "normal_func"

    class MyService(Service):
        async def call(self, ctx):
            pass

    service = MyService()
    assert service.computed_name == "MyService"

    class MyProcessing(BaseProcessing):
        async def call(self, ctx):
            pass

    func_class = MyProcessing()
    service = Service(handler=func_class)
    assert service.computed_name == "MyProcessing"


def test_waiting_for_service_to_finish_condition():
    pass
