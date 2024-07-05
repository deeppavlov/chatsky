"""
Script
------
The Script module provides a set of `pydantic` models for representing the dialog graph.
These models are used to define the conversation flow, and to determine the appropriate response based on
the user's input and the current state of the conversation.
"""

# %%
from __future__ import annotations
from enum import Enum
import inspect
import logging
from typing import Callable, List, Optional, Any, Dict, Tuple, Union, TYPE_CHECKING

from pydantic import BaseModel, field_validator, validate_call

from .types import Label, LabelType, ConditionType, ConstLabel  # noqa: F401
from .message import Message
from .keywords import Keywords
from .normalization import normalize_condition, normalize_label

if TYPE_CHECKING:
    from chatsky.script.core.context import Context
    from chatsky.pipeline.pipeline.pipeline import Pipeline

logger = logging.getLogger(__name__)


class UserFunctionType(str, Enum):
    LABEL = "label"
    RESPONSE = "response"
    CONDITION = "condition"
    TRANSITION_PROCESSING = "pre_transitions_processing"
    RESPONSE_PROCESSING = "pre_response_processing"


USER_FUNCTION_TYPES: Dict[UserFunctionType, Tuple[Tuple[str, ...], str]] = {
    UserFunctionType.LABEL: (("Context", "Pipeline"), "ConstLabel"),
    UserFunctionType.RESPONSE: (("Context", "Pipeline"), "Message"),
    UserFunctionType.CONDITION: (("Context", "Pipeline"), "bool"),
    UserFunctionType.RESPONSE_PROCESSING: (("Context", "Pipeline"), "None"),
    UserFunctionType.TRANSITION_PROCESSING: (("Context", "Pipeline"), "None"),
}


def _types_equal(signature_type: Any, expected_type: str) -> bool:
    """
    This function checks equality of signature type with expected type.
    Three cases are handled. If no signature is present, it is presumed that types are equal.
    If signature is a type, it is compared with expected type as is.
    If signature is a string, it is compared with expected type name.

    :param signature_type: type received from function signature.
    :param expected_type: expected type - a class.
    :return: true if types are equal, false otherwise.
    """
    signature_str = signature_type.__name__ if hasattr(signature_type, "__name__") else str(signature_type)
    signature_empty = signature_type == inspect.Parameter.empty
    expected_string = signature_str == expected_type
    expected_global = str(signature_type) == str(globals().get(expected_type))
    return signature_empty or expected_string or expected_global


def _validate_callable(callable: Callable, func_type: UserFunctionType, flow_label: str, node_label: str) -> List:
    """
    This function validates a function during :py:class:`~chatsky.script.Script` validation.
    It checks parameter number (unconditionally), parameter types (if specified) and return type (if specified).

    :param callable: Function to validate.
    :param func_type: Type of the function (label, condition, response, etc.).
    :param flow_label: Flow label this function is related to (used for error localization only).
    :param node_label: Node label this function is related to (used for error localization only).
    :return: list of produced error messages.
    """

    error_msgs = list()
    signature = inspect.signature(callable)
    arguments_type, return_type = USER_FUNCTION_TYPES[func_type]
    params = list(signature.parameters.values())
    if len(params) != len(arguments_type):
        msg = (
            f"Incorrect parameter number for {callable.__name__!r}: "
            f"should be {len(arguments_type)}, not {len(params)}. "
            f"Error found at {(flow_label, node_label)!r}."
        )
        error_msgs.append(msg)
    for idx, param in enumerate(params):
        if not _types_equal(param.annotation, arguments_type[idx]):
            msg = (
                f"Incorrect parameter annotation for parameter #{idx + 1} "
                f" of {callable.__name__!r}: "
                f"should be {arguments_type[idx]}, not {param.annotation}. "
                f"Error found at {(flow_label, node_label)!r}."
            )
            error_msgs.append(msg)
    if not _types_equal(signature.return_annotation, return_type):
        msg = (
            f"Incorrect return type annotation of {callable.__name__!r}: "
            f"should be {return_type!r}, not {signature.return_annotation}. "
            f"Error found at {(flow_label, node_label)!r}."
        )
        error_msgs.append(msg)
    return error_msgs


class Node(BaseModel, extra="forbid", validate_assignment=True):
    """
    The class for the `Node` object.
    """

    transitions: Dict[Label, ConditionType] = {}
    response: Optional[Union[Message, Callable[[Context, Pipeline], Message]]] = None
    pre_transitions_processing: Dict[Any, Callable] = {}
    pre_response_processing: Dict[Any, Callable] = {}
    misc: dict = {}

    @field_validator("transitions", mode="before")
    @classmethod
    @validate_call
    def normalize_transitions(cls, transitions: Dict[Label, ConditionType]) -> Dict[Label, Callable]:
        """
        The function which is used to normalize transitions and returns normalized dict.

        :param transitions: Transitions to normalize.
        :return: Transitions with normalized label and condition.
        """
        transitions = {
            normalize_label(label): normalize_condition(condition) for label, condition in transitions.items()
        }
        return transitions


class Script(BaseModel, extra="forbid"):
    """
    The class for the `Script` object.
    """

    script: Dict[LabelType, Dict[LabelType, Node]]

    @field_validator("script", mode="before")
    @classmethod
    @validate_call
    def normalize_script(cls, script: Dict[LabelType, Any]) -> Dict[LabelType, Dict[LabelType, Dict[str, Any]]]:
        """
        This function normalizes :py:class:`.Script`: it returns dict where the GLOBAL node is moved
        into the flow with the GLOBAL name. The function returns the structure

        `{GLOBAL: {...NODE...}, ...}` -> `{GLOBAL: {GLOBAL: {...NODE...}}, ...}`.

        :param script: :py:class:`.Script` that describes the dialog scenario.
        :return: Normalized :py:class:`.Script`.
        """
        if isinstance(script, dict):
            if Keywords.GLOBAL in script and all(
                [isinstance(item, Keywords) for item in script[Keywords.GLOBAL].keys()]
            ):
                script[Keywords.GLOBAL] = {Keywords.GLOBAL: script[Keywords.GLOBAL]}
        return script

    @field_validator("script", mode="before")
    @classmethod
    @validate_call
    def validate_script_before(cls, script: Dict[LabelType, Any]) -> Dict[LabelType, Dict[LabelType, Dict[str, Any]]]:
        error_msgs = []
        for flow_name, flow in script.items():
            for node_name, node in flow.items():
                # validate labeling
                transitions = node.get("transitions", dict())
                for label in transitions.keys():
                    if callable(label):
                        error_msgs += _validate_callable(label, UserFunctionType.LABEL, flow_name, node_name)

                # validate responses
                response = node.get("response", None)
                if callable(response):
                    error_msgs += _validate_callable(
                        response,
                        UserFunctionType.RESPONSE,
                        flow_name,
                        node_name,
                    )

                # validate conditions
                for label, condition in transitions.items():
                    if callable(condition):
                        error_msgs += _validate_callable(
                            condition,
                            UserFunctionType.CONDITION,
                            flow_name,
                            node_name,
                        )

                # validate pre_transitions- and pre_response_processing
                pre_transitions_processing = node.get("pre_transitions_processing", dict())
                pre_response_processing = node.get("pre_response_processing", dict())
                for place, functions in zip(
                    (UserFunctionType.TRANSITION_PROCESSING, UserFunctionType.RESPONSE_PROCESSING),
                    (pre_transitions_processing, pre_response_processing),
                ):
                    for function in functions.values():
                        if callable(function):
                            error_msgs += _validate_callable(
                                function,
                                place,
                                flow_name,
                                node_name,
                            )
        if error_msgs:
            error_number_string = "1 error" if len(error_msgs) == 1 else f"{len(error_msgs)} errors"
            raise ValueError(
                f"Found {error_number_string}:\n" + "\n".join([f"{i}) {er}" for i, er in enumerate(error_msgs, 1)])
            )
        else:
            return script

    @field_validator("script", mode="after")
    @classmethod
    @validate_call
    def validate_script_after(cls, script: Dict[LabelType, Any]) -> Dict[LabelType, Dict[LabelType, Dict[str, Any]]]:
        error_msgs = []
        for flow_name, flow in script.items():
            for node_name, node in flow.items():
                # validate labeling
                for label in node.transitions.keys():
                    if not callable(label):
                        norm_flow_label, norm_node_label, _ = normalize_label(label, flow_name)
                        if norm_flow_label not in script.keys():
                            msg = (
                                f"Flow {norm_flow_label!r} cannot be found for label={label}. "
                                f"Error found at {(flow_name, node_name)!r}."
                            )
                        elif norm_node_label not in script[norm_flow_label].keys():
                            msg = (
                                f"Node {norm_node_label!r} cannot be found for label={label}. "
                                f"Error found at {(flow_name, node_name)!r}."
                            )
                        else:
                            msg = None
                        if msg is not None:
                            error_msgs.append(msg)

        if error_msgs:
            error_number_string = "1 error" if len(error_msgs) == 1 else f"{len(error_msgs)} errors"
            raise ValueError(
                f"Found {error_number_string}:\n" + "\n".join([f"{i}) {er}" for i, er in enumerate(error_msgs, 1)])
            )
        else:
            return script

    def __getitem__(self, key):
        return self.script[key]

    def get(self, key, value=None):
        return self.script.get(key, value)

    def keys(self):
        return self.script.keys()

    def items(self):
        return self.script.items()

    def values(self):
        return self.script.values()

    def __iter__(self):
        return self.script.__iter__()
