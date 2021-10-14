from typing import Union, Callable
from enum import Enum, auto


NodeLabel1Type = tuple[str, float]
NodeLabel2Type = tuple[str, str]
NodeLabel3Type = tuple[str, str, float]

NodeLabelTupledType = Union[NodeLabel1Type, NodeLabel2Type, NodeLabel3Type]
NodeLabelType = Union[Callable, NodeLabelTupledType, str]
ConditionType = Callable


# TODO: add description for ActorStage
class ActorStage(Enum):
    GET_PREVIOUS_NODE = auto()
    GET_TRUE_LABEL = auto()
    GET_NEXT_NODE = auto()
    RUN_PROCESSING = auto()
    CREATE_RESPONSE = auto()
