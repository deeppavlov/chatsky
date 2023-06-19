"""
Types
-----
The Types module contains a set of basic data types that
are used to define the expected input and output of various components of the framework.
The types defined in this module include basic data types such as strings
and lists, as well as more complex types that are specific to the framework.
"""
from typing import Union, Callable, Tuple
from enum import Enum, auto
from typing_extensions import TypeAlias

from .keywords import Keywords

LabelType: TypeAlias = Union[str, Keywords]
"""Label can be a casual string or :py:class:`~dff.script.Keywords`."""

NodeLabel1Type: TypeAlias = Tuple[str, float]
"""Label type for transitions can be `[node_name, transition_priority]`."""

NodeLabel2Type: TypeAlias = Tuple[str, str]
"""Label type for transitions can be `[flow_name, node_name]`."""

NodeLabel3Type: TypeAlias = Tuple[str, str, float]
"""Label type for transitions can be `[flow_name, node_name, transition_priority]`."""

NodeLabelTupledType: TypeAlias = Union[NodeLabel1Type, NodeLabel2Type, NodeLabel3Type]
"""Label type for transitions can be one of three different types."""

NodeLabelType: TypeAlias = Union[Callable, NodeLabelTupledType, str]
"""Label type for transitions can be one of three different types."""

ConditionType: TypeAlias = Callable
"""Condition type can be only `Callable`."""

ModuleName: TypeAlias = "str"
"""
Module name names addon state, or your own module state. For example module name can be `"dff_context_storages"`.
"""
# TODO: change example


class ActorStage(Enum):
    """
    The class which holds keys for the handlers. These keys are used
    for the actions of :py:class:`.Actor`. Each stage represents
    a specific step in the conversation flow. Here is a brief description
    of each stage.
    """

    CONTEXT_INIT = auto()
    """
    This stage is used for the context initialization.
    It involves setting up the conversation context.
    """

    GET_PREVIOUS_NODE = auto()
    """
    This stage is used to retrieve the previous node.
    """

    REWRITE_PREVIOUS_NODE = auto()
    """
    This stage is used to rewrite the previous node.
    It involves updating the previous node in the conversation history
    to reflect any changes made during the current conversation turn.
    """

    RUN_PRE_TRANSITIONS_PROCESSING = auto()
    """
    This stage is used for running pre-transitions processing.
    It involves performing any necessary pre-processing tasks.
    """

    GET_TRUE_LABELS = auto()
    """
    This stage is used to retrieve the true labels.
    It involves determining the correct label to take based
    on the current conversation context.
    """

    GET_NEXT_NODE = auto()
    """
    This stage is used to retrieve the next node in the conversation flow.
    """

    REWRITE_NEXT_NODE = auto()
    """
    This stage is used to rewrite the next node.
    It involves updating the next node in the conversation flow
    to reflect any changes made during the current conversation turn.
    """

    RUN_PRE_RESPONSE_PROCESSING = auto()
    """
    This stage is used for running pre-response processing.
    It involves performing any necessary pre-processing tasks
    before generating the response to the user.
    """

    CREATE_RESPONSE = auto()
    """
    This stage is used for response creation.
    It involves generating a response to the user based on the
    current conversation context and any pre-processing performed.
    """

    FINISH_TURN = auto()
    """
    This stage is used for finishing the current conversation turn.
    It involves wrapping up any loose ends, such as saving context,
    before waiting for the user's next input.
    """
