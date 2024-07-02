from pydantic import ValidationError
import pytest

from chatsky.pipeline import Pipeline
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


class TestResponseValidation:
    def test_param_number(self):
        with pytest.raises(ValidationError, match=r"Found 3 errors:[\w\W]*Incorrect parameter number") as e:
            Script(script={"root": {"start": {RESPONSE: UserFunctionSamples.wrong_param_number}}})
        assert e

    def test_param_types(self):
        with pytest.raises(ValidationError, match=r"Found 3 errors:[\w\W]*Incorrect parameter annotation") as e:
            Script(script={"root": {"start": {RESPONSE: UserFunctionSamples.wrong_param_types}}})
        assert e

    def test_return_type(self):
        with pytest.raises(ValidationError, match=r"Found 1 error:[\w\W]*Incorrect return type annotation") as e:
            Script(script={"root": {"start": {RESPONSE: UserFunctionSamples.wrong_return_type}}})
        assert e

    def test_correct_script(self):
        Script(script={"root": {"start": {RESPONSE: UserFunctionSamples.correct_response}}})


class TestConditionValidation:
    def test_param_number(self):
        with pytest.raises(ValidationError, match=r"Found 3 errors:[\w\W]*Incorrect parameter number") as e:
            Script(
                script={
                    "root": {"start": {TRANSITIONS: {("root", "start", 1): UserFunctionSamples.wrong_param_number}}}
                }
            )
        assert e

    def test_param_types(self):
        with pytest.raises(ValidationError, match=r"Found 3 errors:[\w\W]*Incorrect parameter annotation") as e:
            Script(
                script={"root": {"start": {TRANSITIONS: {("root", "start", 1): UserFunctionSamples.wrong_param_types}}}}
            )
        assert e

    def test_return_type(self):
        with pytest.raises(ValidationError, match=r"Found 1 error:[\w\W]*Incorrect return type annotation") as e:
            Script(
                script={"root": {"start": {TRANSITIONS: {("root", "start", 1): UserFunctionSamples.wrong_return_type}}}}
            )
        assert e

    def test_correct_script(self):
        Script(script={"root": {"start": {TRANSITIONS: {("root", "start", 1): UserFunctionSamples.correct_condition}}}})


class TestProcessingValidation:
    def test_response_param_number(self):
        with pytest.raises(ValidationError, match=r"Found 3 errors:[\w\W]*Incorrect parameter number") as e:
            Script(
                script={"root": {"start": {PRE_RESPONSE_PROCESSING: {"PRP": UserFunctionSamples.wrong_param_number}}}}
            )
        assert e

    def test_response_param_types(self):
        with pytest.raises(ValidationError, match=r"Found 3 errors:[\w\W]*Incorrect parameter annotation") as e:
            Script(
                script={"root": {"start": {PRE_RESPONSE_PROCESSING: {"PRP": UserFunctionSamples.wrong_param_types}}}}
            )
        assert e

    def test_response_return_type(self):
        with pytest.raises(ValidationError, match=r"Found 1 error:[\w\W]*Incorrect return type annotation") as e:
            Script(
                script={"root": {"start": {PRE_RESPONSE_PROCESSING: {"PRP": UserFunctionSamples.wrong_return_type}}}}
            )
        assert e

    def test_response_correct_script(self):
        Script(
            script={
                "root": {
                    "start": {PRE_RESPONSE_PROCESSING: {"PRP": UserFunctionSamples.correct_pre_response_processor}}
                }
            }
        )

    def test_transition_param_number(self):
        with pytest.raises(ValidationError, match=r"Found 3 errors:[\w\W]*Incorrect parameter number") as e:
            Script(
                script={
                    "root": {"start": {PRE_TRANSITIONS_PROCESSING: {"PTP": UserFunctionSamples.wrong_param_number}}}
                }
            )
        assert e

    def test_transition_param_types(self):
        with pytest.raises(ValidationError, match=r"Found 3 errors:[\w\W]*Incorrect parameter annotation") as e:
            Script(
                script={"root": {"start": {PRE_TRANSITIONS_PROCESSING: {"PTP": UserFunctionSamples.wrong_param_types}}}}
            )
        assert e

    def test_transition_return_type(self):
        with pytest.raises(ValidationError, match=r"Found 1 error:[\w\W]*Incorrect return type annotation") as e:
            Script(
                script={"root": {"start": {PRE_TRANSITIONS_PROCESSING: {"PTP": UserFunctionSamples.wrong_return_type}}}}
            )
        assert e

    def test_transition_correct_script(self):
        Script(
            script={
                "root": {
                    "start": {PRE_TRANSITIONS_PROCESSING: {"PTP": UserFunctionSamples.correct_pre_transition_processor}}
                }
            }
        )
