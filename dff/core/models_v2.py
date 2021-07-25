# %%

from typing import Union, Callable, Any, Pattern

from pydantic import BaseModel, conlist, validator

CONDITION_DEPTH_TYPE_CHECKING = 20

NodeLabelTupledType = Union[
    tuple[str, float],
    tuple[str, str],
    tuple[str, str, float],
]
NodeLabelType = Union[Callable, NodeLabelTupledType, str]
ConditionType = Any
for _ in range(CONDITION_DEPTH_TYPE_CHECKING):
    ConditionType = Union[conlist(ConditionType, min_items=1), Callable, Pattern, str]


class Transition(BaseModel):
    global_transition: dict[NodeLabelType, ConditionType] = {}
    transition: dict[NodeLabelType, ConditionType] = {}


class Node(Transition):
    response: Union[conlist(str, min_items=1), str, Callable]
    processing: Callable = None


class Flow(Transition):
    graph: dict[str, Node] = {}


class Flows(BaseModel):
    flows: dict[str, Flow]

    @validator("flows")
    def validate_flows(cls, fields: dict) -> dict:
        if not any(fields.values()):
            raise ValueError("expected not empty flows")
        return fields
