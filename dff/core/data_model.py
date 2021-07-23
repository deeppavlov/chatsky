# %%

# from typing import Deque, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple, Union, Callable
from typing import Union, Callable
import re

from pydantic import BaseModel, ValidationError, root_validator, validate_arguments, validator


def hash_obj(obj):
    field_names, field_values = list(zip(*obj))
    return ":".join(["" if val is None else repr(val) for val in field_values])


class ToState(BaseModel):
    flow_name: str = None
    state_name: str = None
    priority: float = None
    callback: Callable = None

    @root_validator
    def check_empty(cls, fields: dict) -> dict:
        required_fields = ["state_name", "callback"]
        if all(fields.get(field) is None for field in required_fields):
            raise ValueError(f"one of {required_fields} expected not None but all of them are None")
        return fields

    @validate_arguments
    def parse(obj: Union[tuple, list, str, Callable]):
        if isinstance(obj, tuple) or isinstance(obj, list):
            return ToState.parse_iterable(obj)
        else:
            state_name, callback = (None, obj) if isinstance(obj, Callable) else (obj, None)
            return ToState(state_name=state_name, callback=callback)

    @validate_arguments
    def parse_iterable(obj: Union[tuple, list]):
        callbacks = [o for o in obj if isinstance(o, Callable)]
        if callbacks:
            return ToState(callback=callbacks[-1])
        elif len(obj) == 1:
            return ToState(state_name=obj[0])
        elif len(obj) == 2:
            try:
                return ToState(priority=obj[1], state_name=obj[0])
            except ValidationError:
                pass
            try:
                return ToState(flow_name=obj[0], state_name=obj[1])
            except ValidationError:
                pass
            raise ValueError(
                f" list[str,Union[str,Callable]] or list[Union[str,Callable], float] "
                f"types expected but got {type(obj)} of {obj}"
            )
        elif len(obj) == 3:
            return ToState(flow_name=obj[0], priority=obj[2], state_name=obj[1])
        else:
            raise ValueError(f"Expected iterable length in range [1,2,3], but got length {len(obj)} of {obj}")

    def hash(self):
        return hash_obj(self)


class Condition(BaseModel):
    string: str = None
    pattern: str = None
    complex_condition: Union[list, tuple] = None
    callback: Callable = None

    @root_validator
    def check_empty(cls, fields: dict) -> dict:
        if not any(fields.values()):
            raise ValueError(f"one of {list(fields.keys())} expected not None but all of them are None")
        return fields

    def parse(obj: Union[tuple, list, str, Callable, re.Pattern]):
        if isinstance(obj, Callable):
            return Condition(callback=obj)
        elif isinstance(obj, re.Pattern):
            return Condition(pattern=obj.pattern)
        elif isinstance(obj, list) or isinstance(obj, list):
            return Condition(complex_condition=obj)
        else:
            return Condition(string=obj)

    def hash(self):
        return hash_obj(self)


ToStateType = Union[str, tuple, Callable]
ConditionType = Union[tuple, list, str, Callable]


class Transition(BaseModel):
    global_to_states: dict[ToStateType, ConditionType] = None
    to_states: dict[ToStateType, ConditionType] = None

    @validator("to_states")
    @validator("global_to_states")
    def check_ts(cls, field: dict[ToStateType, ConditionType]) -> dict[ToStateType, ConditionType]:
        ts2conds = {}
        for key, val in field.items():
            to_st = ToState.parse(key)
            condition = Condition.parse(val)
            to_states[to_st.hash()] = to_st
            conditions[condition.hash()] = condition
            ts2conds[to_st.hash()] = condition.hash()
        return ts2conds


class Node(Transition):
    response: Union[tuple, list, str, Callable] = None
    processing: Callable = None


to_states = {}
conditions = {}


class Flow(Transition):
    graph: dict[str, Node] = None


class Script(BaseModel):
    flows: dict[str, Flow]


GLOBAL_TO_STATES = "global_to_states"
TO_STATES = "to_states"
RESPONSE = "response"
PROCESSING = "processing"
GRAPH = "graph"
script = {
    "globals": {
        GLOBAL_TO_STATES: {"213": any},
        TO_STATES: {"213": any},
        GRAPH: {"node": {GLOBAL_TO_STATES: {"213": any}, RESPONSE: "qweqwdqwd", PROCESSING: any}},
    }
}
s1 = Script(flows=script)
s1.dict()
# %%
list(zip(*list(conditions.values())[0]))

# %%
list(conditions.values())[0].hash()
