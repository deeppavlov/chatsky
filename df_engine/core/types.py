"""
Types
---------------------------
Basic types are defined here.
"""
from typing import Union, Callable
from enum import Enum, auto

from .keywords import Keywords

LabelType = Union[str, Keywords]
"""label can be a casual string or :py:class:`~df_engine.core.keywords.Keywords`"""

NodeLabel1Type = tuple[str, float]
"""label type for transitions can be [node_name, transition_priority]"""

NodeLabel2Type = tuple[str, str]
"""label type for transitions can be [flow_name, node_name]"""

NodeLabel3Type = tuple[str, str, float]
"""label type for transitions can be [flow_name, node_name, transition_priority]"""

NodeLabelTupledType = Union[NodeLabel1Type, NodeLabel2Type, NodeLabel3Type]
"""label type for transitions can be one of three different types"""

NodeLabelType = Union[Callable, NodeLabelTupledType, str]
"""label type for transitions can be one of three different types"""

ConditionType = Callable
"""condition type can be only callable"""


# TODO: add description for each stage of ActorStage
class ActorStage(Enum):
    """
    The class which holds keys for the handlers. These keys are used later
    for the actions of :py:class:`~df_engine.core.actor.Actor`.

    Enums:

    CONTEXT_INIT

    GET_PREVIOUS_NODE

    GET_TRUE_LABELS

    GET_NEXT_NODE

    REWRITE_NEXT_NODE

    RUN_PROCESSING

    CREATE_RESPONSE

    FINISH_TURN
    """

    CONTEXT_INIT = auto()
    GET_PREVIOUS_NODE = auto()
    GET_TRUE_LABELS = auto()
    GET_NEXT_NODE = auto()
    REWRITE_NEXT_NODE = auto()
    RUN_PROCESSING = auto()
    CREATE_RESPONSE = auto()
    FINISH_TURN = auto()
