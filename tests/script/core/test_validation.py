from pydantic import ValidationError
import pytest

from dff.pipeline import Pipeline
from dff.script import (
    PRE_RESPONSE_PROCESSING,
    PRE_TRANSITIONS_PROCESSING,
    RESPONSE,
    TRANSITIONS,
    Context,
    Message,
    Script,
    NodeLabel3Type,
)
from dff.script.conditions import exact_match


def wrong_param_number(number: int) -> float:
    return 8.0 + number


def wrong_param_types(number: int, flag: bool) -> float:
    return 8.0 + number if flag else 42.1


def wrong_return_type(_: Context, __: Pipeline) -> float:
    return 1.0


def correct_label(_: Context, __: Pipeline) -> NodeLabel3Type:
    return ("root", "start", 1)


def correct_response(_: Context, __: Pipeline) -> Message:
    return Message("hi")


def correct_condition(_: Context, __: Pipeline) -> bool:
    return True


def correct_pre_response_processor(_: Context, __: Pipeline) -> None:
    pass


def correct_pre_transition_processor(_: Context, __: Pipeline) -> None:
    pass


class TestLabelValidation:
    def test_param_number(self):
        with pytest.raises(ValidationError, match=r"Incorrect parameter number") as e:
            Script(script={"root": {"start": {TRANSITIONS: {wrong_param_number: exact_match(Message("hi"))}}}})
        assert e

    def test_param_types(self):
        with pytest.raises(ValidationError, match=r"Incorrect \d+ parameter annotation") as e:
            Script(script={"root": {"start": {TRANSITIONS: {wrong_param_types: exact_match(Message("hi"))}}}})
        assert e

    def test_return_type(self):
        with pytest.raises(ValidationError, match=r"Incorrect return type annotation") as e:
            Script(script={"root": {"start": {TRANSITIONS: {wrong_return_type: exact_match(Message("hi"))}}}})
        assert e

    def test_flow_name(self):
        with pytest.raises(ValidationError, match=r"Flow label") as e:
            Script(script={"root": {"start": {TRANSITIONS: {("other", "start", 1): exact_match(Message("hi"))}}}})
        assert e

    def test_node_name(self):
        with pytest.raises(ValidationError, match=r"Node label") as e:
            Script(script={"root": {"start": {TRANSITIONS: {("root", "other", 1): exact_match(Message("hi"))}}}})
        assert e

    def test_correct_script(self):
        Script(script={"root": {"start": {TRANSITIONS: {correct_label: exact_match(Message("hi"))}}}})


class TestResponseValidation:
    def test_param_number(self):
        with pytest.raises(ValidationError, match=r"Incorrect parameter number") as e:
            Script(script={"root": {"start": {RESPONSE: wrong_param_number}}})
        assert e

    def test_param_types(self):
        with pytest.raises(ValidationError, match=r"Incorrect \d+ parameter annotation") as e:
            Script(script={"root": {"start": {RESPONSE: wrong_param_types}}})
        assert e

    def test_return_type(self):
        with pytest.raises(ValidationError, match=r"Incorrect return type annotation") as e:
            Script(script={"root": {"start": {RESPONSE: wrong_return_type}}})
        assert e

    def test_correct_script(self):
        Script(script={"root": {"start": {RESPONSE: correct_response}}})


class TestConditionValidation:
    def test_param_number(self):
        with pytest.raises(ValidationError, match=r"Incorrect parameter number") as e:
            Script(script={"root": {"start": {TRANSITIONS: {("root", "start", 1): wrong_param_number}}}})
        assert e

    def test_param_types(self):
        with pytest.raises(ValidationError, match=r"Incorrect \d+ parameter annotation") as e:
            Script(script={"root": {"start": {TRANSITIONS: {("root", "start", 1): wrong_param_types}}}})
        assert e

    def test_return_type(self):
        with pytest.raises(ValidationError, match=r"Incorrect return type annotation") as e:
            Script(script={"root": {"start": {TRANSITIONS: {("root", "start", 1): wrong_return_type}}}})
        assert e

    def test_correct_script(self):
        Script(script={"root": {"start": {TRANSITIONS: {("root", "start", 1): correct_condition}}}})


class TestProcessingValidation:
    def test_response_param_number(self):
        with pytest.raises(ValidationError, match=r"Incorrect parameter number") as e:
            Script(script={"root": {"start": {PRE_RESPONSE_PROCESSING: {"PRP": wrong_param_number}}}})
        assert e

    def test_response_param_types(self):
        with pytest.raises(ValidationError, match=r"Incorrect \d+ parameter annotation") as e:
            Script(script={"root": {"start": {PRE_RESPONSE_PROCESSING: {"PRP": wrong_param_types}}}})
        assert e

    def test_response_return_type(self):
        with pytest.raises(ValidationError, match=r"Incorrect return type annotation") as e:
            Script(script={"root": {"start": {PRE_RESPONSE_PROCESSING: {"PRP": wrong_return_type}}}})
        assert e

    def test_response_correct_script(self):
        Script(script={"root": {"start": {PRE_RESPONSE_PROCESSING: {"PRP": correct_pre_response_processor}}}})

    def test_transition_param_number(self):
        with pytest.raises(ValidationError, match=r"Incorrect parameter number") as e:
            Script(script={"root": {"start": {PRE_TRANSITIONS_PROCESSING: {"PTP": wrong_param_number}}}})
        assert e

    def test_transition_param_types(self):
        with pytest.raises(ValidationError, match=r"Incorrect \d+ parameter annotation") as e:
            Script(script={"root": {"start": {PRE_TRANSITIONS_PROCESSING: {"PTP": wrong_param_types}}}})
        assert e

    def test_transition_return_type(self):
        with pytest.raises(ValidationError, match=r"Incorrect return type annotation") as e:
            Script(script={"root": {"start": {PRE_TRANSITIONS_PROCESSING: {"PTP": wrong_return_type}}}})
        assert e

    def test_transition_correct_script(self):
        Script(script={"root": {"start": {PRE_TRANSITIONS_PROCESSING: {"PTP": correct_pre_transition_processor}}}})
