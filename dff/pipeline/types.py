"""
Types
-----
This module contains several classes and special types (see below).
"""
from abc import ABC
from enum import unique, Enum, auto
from typing import Callable, Union, Awaitable, Dict, List, Optional, NewType, Iterable

from dff.context_storages import DBAbstractContextStorage
from dff.script import Context, Actor
from typing_extensions import NotRequired, TypedDict, TypeAlias


_ForwardPipelineComponent = NewType("PipelineComponent", None)
_ForwardService = NewType("Service", _ForwardPipelineComponent)
_ForwardServiceGroup = NewType("ServiceGroup", _ForwardPipelineComponent)
_ForwardComponentExtraHandler = NewType("_ComponentExtraHandler", None)
_ForwardProvider = NewType("ABCProvider", ABC)
_ForwardExtraHandlerFunction = NewType("ExtraHandlerFunction", None)


@unique
class ComponentExecutionState(Enum):
    """
    Enum, representing pipeline component execution state.
    These states are stored in `ctx.framework_keys[PIPELINE_STATE_KEY]`,
    that should always be requested with `NOT_RUN` being default fallback.
    Following states are supported:

    - NOT_RUN: component has not been executed yet (the default one),
    - RUNNING: component is currently being executed,
    - FINISHED: component executed successfully,
    - FAILED: component execution failed.
    """

    NOT_RUN = auto()
    RUNNING = auto()
    FINISHED = auto()
    FAILED = auto()


@unique
class GlobalExtraHandlerType(Enum):
    """
    Enum, representing types of global wrappers, that can be set applied for a pipeline.
    The following types are supported:

    - BEFORE_ALL: function called before each pipeline call,
    - BEFORE: function called before each component,
    - AFTER: function called after each component,
    - AFTER_ALL: function called after each pipeline call.
    """

    BEFORE_ALL = auto()
    BEFORE = auto()
    AFTER = auto()
    AFTER_ALL = auto()


@unique
class ExtraHandlerType(Enum):
    """
    Enum, representing wrapper type, pre- or postprocessing.
    The following types are supported:

    - PREPROCESSING: wrapper function called before component,
    - POSTPROCESSING: wrapper function called after component.
    """

    UNDEFINED = auto()
    BEFORE = auto()
    AFTER = auto()


PIPELINE_STATE_KEY = "PIPELINE"
"""
PIPELINE: storage for services and groups execution status.
Should be used in `ctx.framework_keys[PIPELINE_STATE_KEY]`.
"""


StartConditionCheckerFunction: TypeAlias = Callable[[Context, Actor], bool]
"""
A function type for components `start_conditions`.
Accepts context and actor (current pipeline state), returns boolean (whether service can be launched).
"""


StartConditionCheckerAggregationFunction: TypeAlias = Callable[[Iterable[bool]], bool]
"""
A function type for creating aggregation `start_conditions` for components.
Accepts list of functions (other start_conditions to aggregate), returns boolean (whether service can be launched).
"""


ExtraHandlerConditionFunction: TypeAlias = Callable[[str], bool]
"""
A function type used during global wrappers initialization to determine
whether wrapper should be applied to component with given path or not.
Checks components path to be in whitelist (if defined) and not to be in blacklist (if defined).
Accepts str (component path), returns boolean (whether wrapper should be applied).
"""


ServiceRuntimeInfo: TypeAlias = TypedDict(
    "ServiceRuntimeInfo",
    {
        "name": str,
        "path": str,
        "timeout": Optional[float],
        "asynchronous": bool,
        "execution_state": Dict[str, ComponentExecutionState],
    },
)
"""
Type of dictionary, that is passed to components in runtime.
Contains current component info (`name`, `path`, `timeout`, `asynchronous`).
Also contains `execution_state` - a dictionary,
containing other pipeline components execution stats mapped to their paths.
"""


ExtraHandlerRuntimeInfo: TypeAlias = TypedDict(
    "ExtraHandlerRuntimeInfo",
    {
        "function": _ForwardExtraHandlerFunction,
        "stage": ExtraHandlerType,
        "component": ServiceRuntimeInfo,
    },
)
"""
Type of dictionary, that is passed to wrappers in runtime.
Contains current wrapper info (`name`, `stage`).
Also contains `component` - runtime info dictionary of the component this wrapper is attached to.
"""


ExtraHandlerFunction: TypeAlias = Union[
    Callable[[Context], None],
    Callable[[Context, Actor], None],
    Callable[[Context, Actor, ExtraHandlerRuntimeInfo], None],
]
"""
A function type for creating wrappers (before and after functions).
Can accept current dialog context, actor, attached to the pipeline, and current wrapper info dictionary.
"""


ServiceFunction: TypeAlias = Union[
    Callable[[Context], None],
    Callable[[Context], Awaitable[None]],
    Callable[[Context, Actor], None],
    Callable[[Context, Actor], Awaitable[None]],
    Callable[[Context, Actor, ServiceRuntimeInfo], None],
    Callable[[Context, Actor, ServiceRuntimeInfo], Awaitable[None]],
]
"""
A function type for creating service handlers.
Can accept current dialog context, actor, attached to the pipeline, and current service info dictionary.
Can be both synchronous and asynchronous.
"""


ExtraHandlerBuilder: TypeAlias = Union[
    _ForwardComponentExtraHandler,
    TypedDict(
        "WrapperDict",
        {
            "timeout": NotRequired[Optional[float]],
            "asynchronous": NotRequired[bool],
            "functions": List[ExtraHandlerFunction],
        },
    ),
    List[ExtraHandlerFunction],
]
"""
A type, representing anything that can be transformed to ExtraHandlers.
It can be:

- _ForwardComponentExtraHandler object
- Dictionary, containing keys `timeout`, `asynchronous`, `functions`
"""


ServiceBuilder: TypeAlias = Union[
    ServiceFunction,
    _ForwardService,
    Actor,
    TypedDict(
        "ServiceDict",
        {
            "handler": "ServiceBuilder",
            "before_handler": NotRequired[Optional[ExtraHandlerBuilder]],
            "after_handler": NotRequired[Optional[ExtraHandlerBuilder]],
            "timeout": NotRequired[Optional[float]],
            "asynchronous": NotRequired[bool],
            "start_condition": NotRequired[StartConditionCheckerFunction],
            "name": Optional[str],
        },
    ),
]
"""
A type, representing anything that can be transformed to service.
It can be:

- ServiceFunction (will become handler)
- Service object (will be spread and recreated)
- Actor (will be wrapped in a Service as a handler)
- Dictionary, containing keys that are present in Service constructor parameters
"""


ServiceGroupBuilder: TypeAlias = Union[
    List[Union[ServiceBuilder, List[ServiceBuilder], _ForwardServiceGroup]],
    _ForwardServiceGroup,
]
"""
A type, representing anything that can be transformed to service group.
It can be:

- List of `ServiceBuilders`, `ServiceGroup` objects and lists (recursive)
- `ServiceGroup` object (will be spread and recreated)
"""


PipelineBuilder: TypeAlias = TypedDict(
    "PipelineBuilder",
    {
        "messenger_interface": NotRequired[Optional[_ForwardProvider]],
        "context_storage": NotRequired[Optional[Union[DBAbstractContextStorage, Dict]]],
        "components": ServiceGroupBuilder,
        "before_handler": NotRequired[Optional[ExtraHandlerBuilder]],
        "after_handler": NotRequired[Optional[ExtraHandlerBuilder]],
        "optimization_warnings": NotRequired[bool],
    },
)
"""
A type, representing anything that can be transformed to pipeline.
It can be Dictionary, containing keys that are present in Pipeline constructor parameters.
"""
