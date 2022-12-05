"""
Types
---------------------------
Basic types are defined here.
"""
from typing import Union, Callable, Tuple
from enum import Enum, auto

from .keywords import Keywords

LabelType = Union[str, Keywords]
"""Label can be a casual string or :py:class:`~dff.core.engine.core.keywords.Keywords`."""

NodeLabel1Type = Tuple[str, float]
"""Label type for transitions can be `[node_name, transition_priority]`."""

NodeLabel2Type = Tuple[str, str]
"""Label type for transitions can be `[flow_name, node_name]`."""

NodeLabel3Type = Tuple[str, str, float]
"""Label type for transitions can be `[flow_name, node_name, transition_priority]`."""

NodeLabelTupledType = Union[NodeLabel1Type, NodeLabel2Type, NodeLabel3Type]
"""Label type for transitions can be one of three different types."""

NodeLabelType = Union[Callable, NodeLabelTupledType, str]
"""Label type for transitions can be one of three different types."""

ConditionType = Callable
"""Condition type can be only `Callable`."""

ModuleName = str
"""
Module name names addon state, or your own module state. For example module name can be `"df_db_connector"`.
"""
# todo: change example


# TODO: add description for each stage of ActorStage
class ActorStage(Enum):
    """
    The class which holds keys for the handlers. These keys are used
    for the actions of :py:class:`~dff.core.engine.core.actor.Actor`.

    Enums:

    CONTEXT_INIT: Enum(auto)
        This keyword is used for the context initializing.

    GET_PREVIOUS_NODE: Enum(auto)
        This keyword is used to get the previous node.

    REWRITE_PREVIOUS_NODE: Enum(auto)
        This keyword is used for rewriting the previous node.

    RUN_PRE_TRANSITIONS_PROCESSING: Enum(auto)
        This keyword is used for running pre-transitions processing.

    GET_TRUE_LABELS: Enum(auto)
        This keyword is used to get true labels.

    GET_NEXT_NODE: Enum(auto)
        This keyword is used to get next node.

    REWRITE_NEXT_NODE: Enum(auto)
        This keyword is used to rewrite the next node.

    RUN_PRE_RESPONSE_PROCESSING: Enum(auto)
        This keyword is used for running pre-response processing.

    CREATE_RESPONSE: Enum(auto)
        This keyword is used for the response creation.

    FINISH_TURN: Enum(auto)
        This keyword is used for finish turn.
    """

    CONTEXT_INIT = auto()
    GET_PREVIOUS_NODE = auto()
    REWRITE_PREVIOUS_NODE = auto()
    RUN_PRE_TRANSITIONS_PROCESSING = auto()
    GET_TRUE_LABELS = auto()
    GET_NEXT_NODE = auto()
    REWRITE_NEXT_NODE = auto()
    RUN_PRE_RESPONSE_PROCESSING = auto()
    CREATE_RESPONSE = auto()
    FINISH_TURN = auto()
