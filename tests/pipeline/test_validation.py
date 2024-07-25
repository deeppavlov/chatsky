from pydantic import ValidationError
import pytest

from chatsky.pipeline import (
    Pipeline,
    Service,
    ServiceGroup,
    Actor,
    ComponentExtraHandler,
    ServiceRuntimeInfo,
    BeforeHandler,
)
from chatsky.script import (
    PRE_RESPONSE_PROCESSING,
    PRE_TRANSITIONS_PROCESSING,
    RESPONSE,
    TRANSITIONS,
    Context,
    Message,
    Script,
    ConstLabel,
)
from chatsky.script.conditions import exact_match


class UserFunctionSamples:
    """
    This class contains various examples of user functions along with their signatures.
    """

    @staticmethod
    def wrong_param_number(number: int) -> float:
        return 8.0 + number

    @staticmethod
    def wrong_param_types(number: int, flag: bool) -> float:
        return 8.0 + number if flag else 42.1

    @staticmethod
    def wrong_return_type(_: Context, __: Pipeline) -> float:
        return 1.0

    @staticmethod
    def correct_service_function_1(_: Context):
        pass

    @staticmethod
    def correct_service_function_2(_: Context, __: Pipeline):
        pass

    @staticmethod
    def correct_service_function_3(_: Context, __: Pipeline, ___: ServiceRuntimeInfo):
        pass

    @staticmethod
    def correct_label(_: Context, __: Pipeline) -> ConstLabel:
        return ("root", "start", 1)

    @staticmethod
    def correct_response(_: Context, __: Pipeline) -> Message:
        return Message("hi")

    @staticmethod
    def correct_condition(_: Context, __: Pipeline) -> bool:
        return True

    @staticmethod
    def correct_pre_response_processor(_: Context, __: Pipeline) -> None:
        pass

    @staticmethod
    def correct_pre_transition_processor(_: Context, __: Pipeline) -> None:
        pass


# Need a test for returning an awaitable from a ServiceFunction, ExtraHandlerFunction
class TestServiceValidation:
    def test_param_types(self):
        # This doesn't work. For some reason any callable can be a ServiceFunction
        # Using model_validate doesn't help
        with pytest.raises(ValidationError) as e:
            Service(handler=UserFunctionSamples.wrong_param_types)
            assert e
        Service(handler=UserFunctionSamples.correct_service_function_1)
        Service(handler=UserFunctionSamples.correct_service_function_2)
        Service(handler=UserFunctionSamples.correct_service_function_3)

    def test_param_number(self):
        with pytest.raises(ValidationError) as e:
            Service(handler=UserFunctionSamples.wrong_param_number)
            assert e

    def test_return_type(self):
        with pytest.raises(ValidationError) as e:
            Service(handler=UserFunctionSamples.wrong_return_type)
            assert e

    def test_model_validator(self):
        with pytest.raises(ValidationError) as e:
            # Can't pass a list to handler, it has to be a single function
            Service(handler=[UserFunctionSamples.correct_service_function_2])
            assert e
        with pytest.raises(ValidationError) as e:
            # 'handler' is a mandatory field
            Service(before_handler=UserFunctionSamples.correct_service_function_2)
            assert e
        with pytest.raises(ValidationError) as e:
            # Can't pass None to handler, it has to be a callable function
            # Though I wonder if empty Services should be allowed.
            # I see no reason to allow it.
            Service()
            assert e
        with pytest.raises(TypeError) as e:
            # Python says that two positional arguments were given when only one was expected.
            # This happens before Pydantic's validation, so I think there's nothing we can do.
            Service(UserFunctionSamples.correct_service_function_1)
            assert e
        # But it can work like this.
        # A single function gets cast to the right dictionary here.
        Service.model_validate(UserFunctionSamples.correct_service_function_1)


class TestExtraHandlerValidation:
    def test_correct_functions(self):
        funcs = [UserFunctionSamples.correct_service_function_1, UserFunctionSamples.correct_service_function_2]
        handler = BeforeHandler(funcs)
        assert handler.functions == funcs

    def test_single_function(self):
        single_function = UserFunctionSamples.correct_service_function_1
        handler = BeforeHandler(single_function)
        # Checking that a single function is cast to a list within constructor
        assert handler.functions == [single_function]

    def test_wrong_inputs(self):
        with pytest.raises(ValidationError) as e:
            BeforeHandler(1)
            assert e
        with pytest.raises(ValidationError) as e:
            BeforeHandler([1, 2, 3])
            assert e
        # Wait, this one works. Why?
        with pytest.raises(ValidationError) as e:
            BeforeHandler(functions=BeforeHandler([]))
            assert e

class TestServiceGroupValidation:
    def test_single_service(self):
        func = UserFunctionSamples.correct_service_function_2
        group = ServiceGroup.model_validate(Service(handler=func, after_handler=func))
        assert group.components[0].handler == func
        assert group.components[0].after_handler.functions[0] == func

"""
class TestActorValidation:
class TestPipelineValidation:
"""


class TestLabelValidation:
    def test_param_number(self):
        with pytest.raises(ValidationError, match=r"Found 3 errors:[\w\W]*Incorrect parameter number") as e:
            Script(
                script={
                    "root": {
                        "start": {TRANSITIONS: {UserFunctionSamples.wrong_param_number: exact_match(Message("hi"))}}
                    }
                }
            )
        assert e

    def test_param_types(self):
        with pytest.raises(ValidationError, match=r"Found 3 errors:[\w\W]*Incorrect parameter annotation") as e:
            Script(
                script={
                    "root": {
                        "start": {TRANSITIONS: {UserFunctionSamples.wrong_param_types: exact_match(Message("hi"))}}
                    }
                }
            )
        assert e

    def test_return_type(self):
        with pytest.raises(ValidationError, match=r"Found 1 error:[\w\W]*Incorrect return type annotation") as e:
            Script(
                script={
                    "root": {
                        "start": {TRANSITIONS: {UserFunctionSamples.wrong_return_type: exact_match(Message("hi"))}}
                    }
                }
            )
        assert e

    def test_flow_name(self):
        with pytest.raises(ValidationError, match=r"Found 1 error:[\w\W]*Flow '\w*' cannot be found for label") as e:
            Script(script={"root": {"start": {TRANSITIONS: {("other", "start", 1): exact_match(Message("hi"))}}}})
        assert e

    def test_node_name(self):
        with pytest.raises(ValidationError, match=r"Found 1 error:[\w\W]*Node '\w*' cannot be found for label") as e:
            Script(script={"root": {"start": {TRANSITIONS: {("root", "other", 1): exact_match(Message("hi"))}}}})
        assert e

    def test_correct_script(self):
        Script(
            script={"root": {"start": {TRANSITIONS: {UserFunctionSamples.correct_label: exact_match(Message("hi"))}}}}
        )
