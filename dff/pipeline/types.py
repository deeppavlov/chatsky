"""
Types
-----
The Types module contains several classes and special types that are used throughout the `DFF Pipeline`.
The classes and special types in this module can include data models,
data structures, and other types that are defined for type hinting.
"""
from abc import ABC
from enum import unique, Enum
from typing import Callable, Union, Awaitable, Dict, List, Optional, NewType, Iterable, Any

from dff.context_storages import DBContextStorage
from dff.script import Context, ActorStage, NodeLabel2Type, Script
from typing_extensions import NotRequired, TypedDict, TypeAlias
from pydantic import BaseModel


_ForwardPipeline = NewType("Pipeline", Any)
_ForwardPipelineComponent = NewType("PipelineComponent", Any)
_ForwardService = NewType("Service", _ForwardPipelineComponent)
_ForwardServiceBuilder = NewType("ServiceBuilder", Any)
_ForwardServiceGroup = NewType("ServiceGroup", _ForwardPipelineComponent)
_ForwardComponentExtraHandler = NewType("_ComponentExtraHandler", Any)
_ForwardProvider = NewType("ABCProvider", ABC)
_ForwardExtraHandlerRuntimeInfo = NewType("ExtraHandlerRuntimeInfo", Any)


@unique
class ComponentExecutionState(str, Enum):
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

    NOT_RUN = "NOT_RUN"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


@unique
class GlobalExtraHandlerType(str, Enum):
    """
    Enum, representing types of global wrappers, that can be set applied for a pipeline.
    The following types are supported:

    - BEFORE_ALL: function called before each pipeline call,
    - BEFORE: function called before each component,
    - AFTER: function called after each component,
    - AFTER_ALL: function called after each pipeline call.
    """

    BEFORE_ALL = "BEFORE_ALL"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    AFTER_ALL = "AFTER_ALL"


@unique
class ExtraHandlerType(str, Enum):
    """
    Enum, representing wrapper execution stage: before or after the wrapped function.
    The following types are supported:

    - UNDEFINED: wrapper function with undetermined execution stage,
    - BEFORE: wrapper function called before component,
    - AFTER: wrapper function called after component.
    """

    UNDEFINED = "UNDEFINED"
    BEFORE = "BEFORE"
    AFTER = "AFTER"


PIPELINE_STATE_KEY = "PIPELINE"
"""
PIPELINE: storage for services and groups execution status.
Should be used in `ctx.framework_keys[PIPELINE_STATE_KEY]`.
"""


StartConditionCheckerFunction: TypeAlias = Callable[[Context, _ForwardPipeline], bool]
"""
A function type for components `start_conditions`.
Accepts context and pipeline, returns boolean (whether service can be launched).
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


class ServiceRuntimeInfo(BaseModel):
    """
    Type of object, that is passed to components in runtime.
    Contains current component info (`name`, `path`, `timeout`, `asynchronous`).
    Also contains `execution_state` - a dictionary,
    containing execution states of other components mapped to their paths.
    """

    name: str
    path: str
    timeout: Optional[float]
    asynchronous: bool
    execution_state: Dict[str, ComponentExecutionState]


ExtraHandlerFunction: TypeAlias = Union[
    Callable[[Context], Any],
    Callable[[Context, _ForwardPipeline], Any],
    Callable[[Context, _ForwardPipeline, _ForwardExtraHandlerRuntimeInfo], Any],
]
"""
A function type for creating wrappers (before and after functions).
Can accept current dialog context, pipeline, and current wrapper info.
"""


class ExtraHandlerRuntimeInfo(BaseModel):
    func: ExtraHandlerFunction
    stage: ExtraHandlerType
    component: ServiceRuntimeInfo


"""
Type of object, that is passed to wrappers in runtime.
Contains current wrapper info (`name`, `stage`).
Also contains `component` - runtime info of the component this wrapper is attached to.
"""


ServiceFunction: TypeAlias = Union[
    Callable[[Context], None],
    Callable[[Context], Awaitable[None]],
    Callable[[Context, _ForwardPipeline], None],
    Callable[[Context, _ForwardPipeline], Awaitable[None]],
    Callable[[Context, _ForwardPipeline, ServiceRuntimeInfo], None],
    Callable[[Context, _ForwardPipeline, ServiceRuntimeInfo], Awaitable[None]],
]
"""
A function type for creating service handlers.
Can accept current dialog context, pipeline, and current service info.
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
    str,
    TypedDict(
        "ServiceDict",
        {
            "handler": _ForwardServiceBuilder,
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
- String 'ACTOR' - the pipeline Actor will be placed there
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
        "context_storage": NotRequired[Optional[Union[DBContextStorage, Dict]]],
        "components": ServiceGroupBuilder,
        "before_handler": NotRequired[Optional[ExtraHandlerBuilder]],
        "after_handler": NotRequired[Optional[ExtraHandlerBuilder]],
        "optimization_warnings": NotRequired[bool],
        "script": Union[Script, Dict],
        "start_label": NodeLabel2Type,
        "fallback_label": NotRequired[Optional[NodeLabel2Type]],
        "label_priority": NotRequired[float],
        "validation_stage": NotRequired[Optional[bool]],
        "condition_handler": NotRequired[Optional[Callable]],
        "verbose": NotRequired[bool],
        "handlers": NotRequired[Optional[Dict[ActorStage, List[Callable]]]],
    },
)
"""
A type, representing anything that can be transformed to pipeline.
It can be Dictionary, containing keys that are present in Pipeline constructor parameters.
"""
