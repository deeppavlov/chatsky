import asyncio
from typing import Callable

from pydantic import ValidationError
import pytest

from chatsky.core.service import (
    Service,
    ServiceGroup,
    BeforeHandler,
    PipelineComponent,
)
from chatsky.core import Context, Pipeline
from chatsky.utils.testing import TOY_SCRIPT_KWARGS, TOY_SCRIPT


# Looks overly long, we only need one function anyway.
class UserFunctionSamples:
    """
    This class contains various examples of user functions along with their signatures.
    """

    @staticmethod
    def correct_service_function_1(_: Context):
        pass


# Could make a test for returning an awaitable from a ServiceFunction, ExtraHandlerFunction
class TestServiceValidation:
    def test_model_validator(self):
        with pytest.raises(ValidationError):
            # Can't pass a list to handler, it has to be a single function
            Service(handler=[UserFunctionSamples.correct_service_function_1])
        with pytest.raises(NotImplementedError):
            # Can't pass 'None' to handler, it has to be a callable function
            # Though I wonder if empty Services should be allowed.
            # I see no reason to allow it.
            service = Service()
            asyncio.run(service.call(Context()))
        with pytest.raises(TypeError):
            # Python says that two positional arguments were given when only one was expected.
            # This happens before Pydantic's validation, so I think there's nothing we can do.
            Service(UserFunctionSamples.correct_service_function_1)
        # But it can work like this.
        # A single function gets cast to the right dictionary here.
        Service.model_validate(UserFunctionSamples.correct_service_function_1)


class TestExtraHandlerValidation:
    def test_correct_functions(self):
        funcs = [UserFunctionSamples.correct_service_function_1, UserFunctionSamples.correct_service_function_1]
        handler = BeforeHandler(functions=funcs)
        assert handler.functions == funcs

    def test_single_function(self):
        single_function = UserFunctionSamples.correct_service_function_1
        handler = BeforeHandler.model_validate(single_function)
        # Checking that a single function is cast to a list within constructor
        assert handler.functions == [single_function]

    def test_extra_handler_as_functions(self):
        # 'functions' should be a list of ExtraHandlerFunctions,
        # but you can pass another ExtraHandler there, because, coincidentally,
        # it's a Callable with the right signature. It may be changed later, though.
        BeforeHandler.model_validate({"functions": BeforeHandler(functions=[])})

    def test_wrong_inputs(self):
        with pytest.raises(ValidationError):
            # 1 is not a callable
            BeforeHandler.model_validate(1)
        with pytest.raises(ValidationError):
            # 'functions' should be a list of ExtraHandlerFunctions
            BeforeHandler.model_validate([1, 2, 3])


# Note: I haven't tested components being asynchronous in any way,
# other than in the async pipeline components tutorial.
# It's not a test though.
class TestServiceGroupValidation:
    def test_single_service(self):
        func = UserFunctionSamples.correct_service_function_1
        group = ServiceGroup(components=[Service(handler=func, after_handler=func)])
        assert group.components[0].handler == func
        assert group.components[0].after_handler.functions[0] == func
        # Same, but with model_validate
        group = ServiceGroup.model_validate([Service(handler=func, after_handler=func)])
        assert group.components[0].handler == func
        assert group.components[0].after_handler.functions[0] == func

    def test_several_correct_services(self):
        func = UserFunctionSamples.correct_service_function_1
        services = [Service.model_validate(func), Service(handler=func, timeout=10)]
        group = ServiceGroup(components=services, timeout=15)
        assert group.components == services
        assert group.timeout == 15
        assert group.components[0].timeout is None
        assert group.components[1].timeout == 10

    def test_wrong_inputs(self):
        with pytest.raises(ValidationError):
            # 'components' must be a list of PipelineComponents, wrong type
            # Though 123 will be cast to a list
            ServiceGroup(components=123)
        with pytest.raises(ValidationError):
            # The dictionary inside 'components' will try to get cast to Service and will fail.
            # 'components' must be a list of PipelineComponents, but it's just a normal dictionary (not a Service).
            ServiceGroup(components={"handler": 123})


# Can't think of any other tests that aren't done in other tests in this file
class TestPipelineValidation:
    def test_correct_inputs(self):
        Pipeline(**TOY_SCRIPT_KWARGS)
        Pipeline.model_validate(TOY_SCRIPT_KWARGS)

    def test_fallback_label_set_to_start_label(self):
        pipeline = Pipeline(script=TOY_SCRIPT, start_label=("greeting_flow", "start_node"))
        assert pipeline.fallback_label.node_name == "start_node"

    def test_incorrect_labels(self):
        with pytest.raises(ValidationError):
            Pipeline(script=TOY_SCRIPT, start_label=("nonexistent", "nonexistent"))

        with pytest.raises(ValidationError):
            Pipeline(
                script=TOY_SCRIPT,
                start_label=("greeting_flow", "start_node"),
                fallback_label=("nonexistent", "nonexistent"),
            )

    def test_pipeline_services_cached(self):
        pipeline = Pipeline(**TOY_SCRIPT_KWARGS)
        old_actor_id = id(pipeline.services_pipeline)
        pipeline.fallback_label = ("greeting_flow", "other_node")
        assert old_actor_id == id(pipeline.services_pipeline)

    def test_pre_services(self):
        with pytest.raises(ValidationError):
            # 'pre_services' must be a ServiceGroup
            Pipeline(**TOY_SCRIPT_KWARGS, pre_services=123)


class CustomPipelineComponent(PipelineComponent):
    start_condition: Callable = lambda: True

    def run_component(self, ctx: Context, pipeline: Pipeline):
        pass


class TestPipelineComponentValidation:
    def test_wrong_names(self):
        func = UserFunctionSamples.correct_service_function_1
        with pytest.raises(ValidationError):
            Service(handler=func, name="bad.name")
        with pytest.raises(ValidationError):
            Service(handler=func, name="")

    # todo: move this to component tests
    def test_name_not_defined(self):
        comp = CustomPipelineComponent()
        assert comp.computed_name == "noname_service"
