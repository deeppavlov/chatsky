# %%

from enum import Enum, auto


class MarkupKeywords(Enum):
    TO_STATES = auto()
    GLOBAL_TO_STATES = auto()
    GRAPH = auto()
    RESPONSE = auto()
    PROCESSING = auto()
    # TRIGGERS = auto()


locals().update(MarkupKeywords.__dict__["_member_map_"])


# %%
from enum import Enum, IntEnum

from pydantic import BaseModel, ValidationError


class FruitEnum(str, Enum):
    pear = "pear"
    banana = "banana"


class ToolEnum(IntEnum):
    spanner = 1
    wrench = 2


class CookingModel(BaseModel):
    fruit: FruitEnum = FruitEnum.pear
    tool: ToolEnum = ToolEnum.spanner


# %%
CookingModel(fruit="banana", tool=1).json()
# %%
repr(ert)

# %%
def ert():
    pass


# %%
from typing import Callable
from pydantic import BaseModel, Field
from pydantic import validate_arguments, ValidationError


class Foo(BaseModel):
    callback: Callable[[int], int]


m = Foo(callback=lambda x: x)
print(m)
# %%
m.json()
# %%
from typing import Deque, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple, Union
from pydantic import BaseModel, ValidationError, root_validator


class Foo(BaseModel):
    d: dict[Union[str, Callable], int]


Foo(
    d={
        1: 2,
        3: 2,
        any: 2,
    }
)
# %%
script = {
    # Example of global transitions
    "globals": {
        GLOBAL_TO_STATES: {
            ("helper", "commit_suicide", priorities.high): r"i want to commit suicide",
            ("not_understand", priorities.high): r"i did not understan",
            ("generic_responses_for_extrav", "root", priorities.middle): generic_responses.intent,
        },
        GRAPH: {
            "not_understand": {
                RESPONSE: "Sorry for not being clear",
                TO_STATES: {previous: intents.always_true},
            }
        },
    },
}

# %%
from pydantic import BaseModel, ValidationError, validator

# Union[tuple,Callable,str]
# class NodeName(tuple,str,Callable):
#     pass

ToStateType = Union[str, tuple, Callable]
ConditionType = Union[tuple, list, str, Callable]

to_states = {}
conditions = {}


class Flow(BaseModel):
    global_to_states: dict[ToStateType, ConditionType] = None
    to_states: dict[ToStateType, ConditionType] = None

    @validator("to_states")
    @validator("global_to_states")
    def check_ts(cls, field: dict[ToStateType, ConditionType]) -> dict[ToStateType, ConditionType]:
        ts2conds = {}
        for key, val in field.items():
            to_st = ToState.parse(key)
            condition = Condititon.parse(val)
            to_states[repr(to_st)] = to_st
            conditions[repr(condition)] = condition
            ts2conds[repr(to_st)] = repr(condition)
        return ts2conds


class Script(BaseModel):
    flows: dict[str, Flow]


GLOBAL_TO_STATES = "global_to_states"
TO_STATES = "to_states"
script = {"globals": {GLOBAL_TO_STATES: {"213": "srr"}, TO_STATES: {"213": "srr"}}}
s1 = Script(flows=script)
s1.dict()
# %%
to_states
# %%
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


import itertools

# tests
def test_ts():
    good_graphs = ["flow_name", "123"]
    good_states = ["state_name", "123"]
    good_states_with_lambda = good_states + [lambda x: "state"]
    good_priorities = [123, 0, 0.1, -1, "123", "0", "0.1", "-1"]
    samples = (
        good_states
        + list(itertools.product(good_graphs, good_states_with_lambda))
        + list(itertools.product(good_states_with_lambda, good_priorities))
        + list(itertools.product(good_graphs, good_states_with_lambda, good_priorities))
    )
    for sample in samples:
        try:
            ToState.parse(sample)
        except ValidationError as exc:
            print(sample)
            raise exc
    # negative sampling
    bad_states = [None]
    bad_priorities = ["0<zx", "0.1c", "<zx"]
    samples = list(itertools.product(good_graphs, bad_states, good_priorities)) + list(
        itertools.product(good_graphs, good_states, bad_priorities)
    )
    for sample in samples:
        try:
            res = ToState.parse(sample)
            raise Exception(f"{sample} couldn't be passed but get {res}")
        except ValidationError:
            continue


test_ts()

# %%
import re


class Condititon(BaseModel):
    string: str = None
    pattern: str = None
    complex_condition: Union[list, tuple] = None
    callback: Callable = None

    @root_validator
    def check_empty(cls, fields: dict) -> dict:
        print(fields.values())
        if not any(fields.values()):
            raise ValueError(f"one of {list(fields.keys())} expected not None but all of them are None")
        return fields

    def parse(obj: Union[tuple, list, str, Callable, re.Pattern]):
        print(obj)
        if isinstance(obj, Callable):
            return Condititon(callback=obj)
        elif isinstance(obj, re.Pattern):
            return Condititon(pattern=obj.pattern)
        elif isinstance(obj, list) or isinstance(obj, list):
            return Condititon(complex_condition=obj)
        else:
            return Condititon(string=obj)

# tests
def test_cond():
    samples = ["sample", "123", re.compile("123"), any, [any,["123", "123"]], 123]
    for sample in samples:
        try:
            Condititon.parse(sample)
        except ValidationError as exc:
            print(sample)
            raise exc
    # negative sampling
    samples = [None]
    for sample in samples:
        try:
            res = Condititon.parse(sample)
            raise Exception(f"{sample} couldn't be passed but get {res}")
        except ValidationError:
            continue


test_cond()
# %%