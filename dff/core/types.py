from typing import Union, Callable
from enum import Enum, auto

from .keywords import Keywords

LabelType = Union[str, Keywords]

NodeLabel1Type = tuple[str, float]
NodeLabel2Type = tuple[str, str]
NodeLabel3Type = tuple[str, str, float]

NodeLabelTupledType = Union[NodeLabel1Type, NodeLabel2Type, NodeLabel3Type]
NodeLabelType = Union[Callable, NodeLabelTupledType, str]
ConditionType = Callable


# TODO: add description for ActorStage
class ActorStage(Enum):
    CONTEXT_INIT = auto()
    GET_PREVIOUS_NODE = auto()
    GET_TRUE_LABELS = auto()
    GET_NEXT_NODE = auto()
    REWRITE_NEXT_NODE = auto()
    RUN_PROCESSING = auto()
    CREATE_RESPONSE = auto()
    FINISH_TURN = auto()
