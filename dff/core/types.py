from typing import Union, Callable

NodeLabel1Type = tuple[str, float]
NodeLabel2Type = tuple[str, str]
NodeLabel3Type = tuple[str, str, float]

NodeLabelTupledType = Union[NodeLabel1Type, NodeLabel2Type, NodeLabel3Type]
NodeLabelType = Union[Callable, NodeLabelTupledType, str]
ConditionType = Callable
