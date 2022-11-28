"""
Types
---------------------------
Basic types are defined here.
"""
from typing import Union, Callable, Tuple, NewType
from enum import Enum, auto

from .keywords import Keywords


LabelType = NewType("LabelType", Union[str, Keywords])
"""Label can be a casual string or :py:class:`~dff.core.engine.core.keywords.Keywords`."""

NodeLabel1Type = NewType("NodeLabel1Type", Tuple[str, float])
"""Label type for transitions can be `[node_name, transition_priority]`."""

NodeLabel2Type = NewType("NodeLabel2Type", Tuple[str, str])
"""Label type for transitions can be `[flow_name, node_name]`."""

NodeLabel3Type = NewType("NodeLabel3Type", Tuple[str, str, float])
"""Label type for transitions can be `[flow_name, node_name, transition_priority]`."""

NodeLabelTupledType = NewType("NodeLabelTupledType", Union[NodeLabel1Type, NodeLabel2Type, NodeLabel3Type])
"""Label type for transitions can be one of three different types."""

NodeLabelType = NewType("NodeLabelType", Union[Callable, NodeLabelTupledType, str])
"""Label type for transitions can be one of three different types."""

ConditionType = NewType("ConditionType", Callable)
"""Condition type can be only `Callable`."""

ModuleName = NewType("ModuleName", str)
"""
Module name names addon state, or your own module state. For example module name can be `"df_db_connector"`.
"""
# todo: change example


# TODO: add description for each stage of ActorStage
class ActorStage(Enum):
    """
    The class which holds keys for the handlers. These keys are used
    for the actions of :py:class:`~dff.core.engine.core.actor.Actor`.
    """

    #: This keyword is used for the context initializing.
    CONTEXT_INIT = auto()

    #: This keyword is used to get the previous node.
    GET_PREVIOUS_NODE = auto()

    #: This keyword is used for rewriting the previous node.
    REWRITE_PREVIOUS_NODE = auto()

    #: This keyword is used for running pre-transitions processing.
    RUN_PRE_TRANSITIONS_PROCESSING = auto()

    #: This keyword is used to get true labels.
    GET_TRUE_LABELS = auto()

    #: This keyword is used to get next node.
    GET_NEXT_NODE = auto()

    #: This keyword is used to rewrite the next node.
    REWRITE_NEXT_NODE = auto()

    #: This keyword is used for running pre-response processing.
    RUN_PRE_RESPONSE_PROCESSING = auto()

    #: This keyword is used for the response creation.
    CREATE_RESPONSE = auto()

    #: This keyword is used for finish turn.
    FINISH_TURN = auto()
