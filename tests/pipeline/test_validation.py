from pydantic import ValidationError
import pytest

from chatsky.pipeline import (
    Pipeline,
    Service,
    ServiceGroup,
    Actor,
    ServiceRuntimeInfo,
    BeforeHandler,
)
from chatsky.script import Context
from chatsky.utils.testing import TOY_SCRIPT, TOY_SCRIPT_KWARGS


# Looks overly long, we only need one function anyway.
class UserFunctionSamples:
    """
    This class contains various examples of user functions along with their signatures.
    """

    @staticmethod
    def correct_service_function_1(_: Context):
        pass

    @staticmethod
    def correct_service_function_2(_: Context, __: Pipeline):
        pass

    @staticmethod
    def correct_service_function_3(_: Context, __: Pipeline, ___: ServiceRuntimeInfo):
        pass


# Could make a test for returning an awaitable from a ServiceFunction, ExtraHandlerFunction
class TestServiceValidation:
    def test_model_validator(self):
        with pytest.raises(ValidationError):
            # Can't pass a list to handler, it has to be a single function
            Service(handler=[UserFunctionSamples.correct_service_function_2])
        with pytest.raises(ValidationError):
            # Can't pass 'None' to handler, it has to be a callable function
            # Though I wonder if empty Services should be allowed.
            # I see no reason to allow it.
            Service()
        with pytest.raises(TypeError):
            # Python says that two positional arguments were given when only one was expected.
            # This happens before Pydantic's validation, so I think there's nothing we can do.
            Service(UserFunctionSamples.correct_service_function_1)
        # But it can work like this.
        # A single function gets cast to the right dictionary here.
        Service.model_validate(UserFunctionSamples.correct_service_function_1)


class TestExtraHandlerValidation:
    def test_correct_functions(self):
        funcs = [UserFunctionSamples.correct_service_function_1, UserFunctionSamples.correct_service_function_2]
        handler = BeforeHandler(functions=funcs)
        assert handler.functions == funcs

    def test_single_function(self):
        single_function = UserFunctionSamples.correct_service_function_1
        handler = BeforeHandler.model_validate(single_function)
        # Checking that a single function is cast to a list within constructor
        assert handler.functions == [single_function]

    def test_wrong_inputs(self):
        with pytest.raises(ValidationError):
            # 1 is not a callable
            BeforeHandler.model_validate(1)
        with pytest.raises(ValidationError):
            # 'functions' should be a list of ExtraHandlerFunctions
            BeforeHandler.model_validate([1, 2, 3])


# Note: I haven't tested components being asynchronous in any way.
class TestServiceGroupValidation:
    def test_single_service(self):
        func = UserFunctionSamples.correct_service_function_2
        group = ServiceGroup(components=Service(handler=func, after_handler=func))
        assert group.components[0].handler == func
        assert group.components[0].after_handler.functions[0] == func
        # Same, but with model_validate
        group = ServiceGroup.model_validate(Service(handler=func, after_handler=func))
        assert group.components[0].handler == func
        assert group.components[0].after_handler.functions[0] == func

    def test_several_correct_services(self):
        func = UserFunctionSamples.correct_service_function_2
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
            # The dictionary inside 'components' will check if Actor, Service or ServiceGroup fit the signature,
            # but it doesn't fit any of them, so it's just a normal dictionary
            ServiceGroup(components={"before_handler": []})
        with pytest.raises(ValidationError):
            # The dictionary inside 'components' will try to get cast to Service and will fail
            # But 'components' must be a list of PipelineComponents, so it's just a normal dictionary
            ServiceGroup(components={"handler": 123})


# Testing of node and script validation for actor exist at script/core/test_actor.py
class TestActorValidation:
    def test_toy_script_actor(self):
        Actor(**TOY_SCRIPT_KWARGS)

    def test_wrong_inputs(self):
        with pytest.raises(ValidationError):
            # 'condition_handler' is not an Optional field.
            Actor(**TOY_SCRIPT_KWARGS, condition_handler=None)
        with pytest.raises(ValidationError):
            # 'handlers' is not an Optional field.
            Actor(**TOY_SCRIPT_KWARGS, handlers=None)
        with pytest.raises(ValidationError):
            # 'script' must be either a dict or Script instance.
            Actor(script=[], start_label=TOY_SCRIPT_KWARGS["start_label"])


# Can't think of any other tests that aren't done in other tests in this file
class TestPipelineValidation:
    def test_correct_inputs(self):
        Pipeline(**TOY_SCRIPT_KWARGS)
        Pipeline.model_validate(TOY_SCRIPT_KWARGS)

    def test_pre_services(self):
        with pytest.raises(ValidationError):
            # 'pre_services' must be a ServiceGroup
            Pipeline(**TOY_SCRIPT_KWARGS, pre_services=123)