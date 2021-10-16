from typing import Dict, List, Tuple
from typing import Union, Callable
from enum import Enum, auto


NodeLabel1Type = Tuple[str, float]
NodeLabel2Type = Tuple[str, str]
NodeLabel3Type = Tuple[str, str, float]

NodeLabelTupledType = Union[NodeLabel1Type, NodeLabel2Type, NodeLabel3Type]
NodeLabelType = Union[Callable, NodeLabelTupledType, str]
ConditionType = Callable


# TODO: add description for ActorStage
class ActorStage(Enum):
    CONTEXT_INIT = auto()
    GET_PREVIOUS_NODE = auto()
    GET_TRUE_LABELS = auto()
    GET_NEXT_NODE = auto()
    RUN_PROCESSING = auto()
    CREATE_RESPONSE = auto()
