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
from typing import Callable, List, Optional, Any, Dict, Type, Union, TYPE_CHECKING

from pydantic import BaseModel, field_validator, validate_call

from .types import LabelType, NodeLabelType, ConditionType, NodeLabel3Type
from .message import Message
from .keywords import Keywords
from .normalization import normalize_condition, normalize_label

if TYPE_CHECKING:
    from dff.script.core.context import Context
    from dff.pipeline.pipeline.pipeline import Pipeline

logger = logging.getLogger(__name__)


class UserFunctionType(str, Enum):
    LABEL = "label"
    RESPONSE = "response"
    CONDITION = "condition"
    TRANSITION_PROCESSING = "pre_transitions_processing"
    RESPONSE_PROCESSING = "pre_response_processing"


def error_handler(error_msgs: list, msg: str, exception: Optional[Exception] = None):
    """
    This function handles errors during :py:class:`~dff.script.Script` validation.

    :param error_msgs: List that contains error messages. :py:func:`~dff.script.error_handler`
        adds every next error message to that list.
    :param msg: Error message which is to be added into `error_msgs`.
    :param exception: Invoked exception. If it has been set, it is used to obtain logging traceback.
        Defaults to `None`.
    :param logging_flag: The flag which defines whether logging is necessary. Defaults to `True`.
    """
    error_msgs.append(msg)
    logger.error(msg, exc_info=exception)


def types_equal(signature_type: Any, expected_type: Type) -> bool:
    """
    This function checks equality of signature type with expected type.
    Three cases are handled. If no signature is present, it is presumed that types are equal.
    If signature is a type, it is compared with expected type as is.
    If signature is a string, it is compared with expected type name.

    :param signature_type: type received from function signature.
    :param expected_type: expected type - a class.
    :return: true if types are equal, false otherwise.
    """
    signature_empty = signature_type == inspect.Parameter.empty
    types_match = signature_type == expected_type
    expected_string = signature_type == expected_type.__name__
    return signature_empty or types_match or expected_string



def validate_callable(callable: Callable, func_type: UserFunctionType, flow_label: str, node_label: str) -> List:
    """
    This function validates a function during :py:class:`~dff.script.Script` validation.
    It checks parameter number (unconditionally), parameter types (if specified) and return type (if specified).

    :param callable: Function to validate.
    :param func_type: Type of the function (label, condition, response, etc.).
    :param flow_label: Flow label this function is related to (used for error localization only).
    :param node_label: Node label this function is related to (used for error localization only).
    :return: list of produced error messages.
    """
    from dff.script.core.context import Context
    from dff.pipeline.pipeline.pipeline import Pipeline

    USER_FUNCTION_TYPES = {
        UserFunctionType.LABEL: ((Context, Pipeline), None),
        UserFunctionType.RESPONSE: ((Context, Pipeline), Message),
        UserFunctionType.CONDITION: ((Context, Pipeline), bool),
        UserFunctionType.RESPONSE_PROCESSING: ((Context, Pipeline), None),
        UserFunctionType.TRANSITION_PROCESSING: ((Context, Pipeline), None),
    }

    error_msgs = list()
    signature = inspect.signature(callable)
    arguments_type, return_type = USER_FUNCTION_TYPES[func_type]
    params = list(signature.parameters.values())
    if len(params) != len(arguments_type):
        msg = (
            f"Incorrect parameter number of {func_type}={callable.__name__}: "
            f"should be {len(arguments_type)}, found {len(params)}, "
            f"error was found in (flow_label, node_label)={(flow_label, node_label)}"
        )
        error_handler(error_msgs, msg, None)
    for idx, param in enumerate(params):
        if not types_equal(param.annotation, arguments_type[idx]):
            msg = (
                f"Incorrect {idx} parameter annotation of {func_type}={callable.__name__}: "
                f"should be {arguments_type[idx]} ({type(arguments_type[idx])}), "
                f"found {param.annotation} ({type(param.annotation)}), "
                f"error was found in (flow_label, node_label)={(flow_label, node_label)}"
            )
            error_handler(error_msgs, msg, None)
    if not types_equal(signature.return_annotation, return_type):
        msg = (
            f"Incorrect return type annotation of {func_type}={callable.__name__}: "
            f"should be {return_type} ({type(return_type)}), "
            f"found {signature.return_annotation} ({type(signature.return_annotation)}), "
            f"error was found in (flow_label, node_label)={(flow_label, node_label)}"
        )
        error_handler(error_msgs, msg, None)
    return error_msgs


class Node(BaseModel, extra="forbid", validate_assignment=True):
    """
    The class for the `Node` object.
    """

    transitions: Dict[NodeLabelType, ConditionType] = {}
    response: Optional[Union[Message, Callable[[Context, Pipeline], Message]]] = None
    pre_transitions_processing: Dict[Any, Callable] = {}
    pre_response_processing: Dict[Any, Callable] = {}
    misc: dict = {}

    @field_validator("transitions", mode="before")
    @classmethod
    @validate_call
    def normalize_transitions(
        cls, transitions: Dict[NodeLabelType, ConditionType]
    ) -> Dict[Union[Callable, NodeLabel3Type], Callable]:
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

    @field_validator("script", mode="after")
    @classmethod
    @validate_call
    def validate_script(cls, script: Dict[LabelType, Any]) -> Dict[LabelType, Dict[LabelType, Dict[str, Any]]]:
        error_msgs = []
        for flow_name, flow in script.items():
            for node_name, node in flow.items():
                # validate labeling
                for label in node.transitions.keys():
                    if callable(label):
                        error_msgs += validate_callable(label, UserFunctionType.LABEL, flow_name, node_name)
                    else:
                        flow_label, node_label, _ = label
                        if flow_label == "":
                            flow_label = flow_name
                        if flow_label not in script.keys():
                            msg = (
                                f"Flow label {flow_label} can not be found for label={label}, "
                                f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                            )
                        elif node_label not in script[flow_label].keys():
                            msg = (
                                f"Node label {node_label} can not be found for label={label}, "
                                f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                            )
                        else:
                            msg = None
                        if msg is not None:
                            error_handler(error_msgs, msg, None)

                # validate responses
                if callable(node.response):
                    error_msgs += validate_callable(
                        node.response,
                        UserFunctionType.RESPONSE,
                        flow_name,
                        node_name,
                    )
                elif node.response is not None and not isinstance(node.response, Message):
                    msg = (
                        f"Expected type of response is subclass of {Message}, "
                        f"got type(response)={type(node.response)}, "
                        f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                    )
                    error_handler(error_msgs, msg, None)

                # validate conditions
                for label, condition in node.transitions.items():
                    if callable(condition):
                        error_msgs += validate_callable(
                            condition,
                            UserFunctionType.CONDITION,
                            flow_name,
                            node_name,
                        )
                    else:
                        msg = (
                            f"Expected type of condition for label={label} is {Callable}, "
                            f"got type(condition)={type(condition)}, "
                            f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                        )
                        error_handler(error_msgs, msg, None)

                # validate pre_transitions- and pre_response_processing
                for place, functions in zip(
                    (UserFunctionType.TRANSITION_PROCESSING, UserFunctionType.RESPONSE_PROCESSING),
                    (node.pre_transitions_processing, node.pre_response_processing)
                ):
                    for name, function in functions.items():
                        if callable(function):
                            error_msgs += validate_callable(
                                function,
                                place,
                                flow_name,
                                node_name,
                            )
                        else:
                            msg = (
                                f"Expected type of pre_{place}_processing {name} is {Callable}, "
                                f"got type(pre_{place}_processing)={type(function)}, "
                                f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                            )
                            error_handler(error_msgs, msg, None)
        if error_msgs:
            raise ValueError(
                f"Found {len(error_msgs)} errors: " + " ".join([f"{i}) {er}" for i, er in enumerate(error_msgs, 1)])
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
