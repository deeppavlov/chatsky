from abc import ABC
from enum import unique, Enum, auto
from typing import Callable, Any, Union, Awaitable, Dict, List, TypedDict, Optional, NewType, Iterable, Hashable

from df_db_connector import DBAbstractConnector
from df_engine.core import Context, Actor
from typing_extensions import NotRequired


_ForwardPipelineComponent = NewType("PipelineComponent", None)
_ForwardService = NewType("Service", _ForwardPipelineComponent)
_ForwardServiceGroup = NewType("ServiceGroup", _ForwardPipelineComponent)
_ForwardServiceWrapper = NewType("Wrapper", None)
_ForwardProvider = NewType("ABCProvider", ABC)
_ForwardWrapperFunction = NewType("WrapperFunction", None)


@unique
class ComponentExecutionState(Enum):
    """
    Enum, representing pipeline component execution state.
    These states are stored in `ctx.framework_keys[PIPELINE_STATE_KEY]`,
        thety should always be requested with `NOT_RUN` being default fallback.
    Following states are supported:
        NOT_RUN: component has not been executed yet (the default one)
        RUNNING: component is currently being executed
        FINISHED: component executed successfully
        FAILED: component execution failed
    """

    NOT_RUN = auto()
    RUNNING = auto()
    FINISHED = auto()
    FAILED = auto()


@unique
class GlobalWrapperType(Enum):
    """
    Enum, representing types of global wrappers, that can be set applied for a pipeline.
    The following types are supported:
        BEFORE_ALL: function called before each pipeline call
        BEFORE: function called before each component
        AFTER: function called after each component
        AFTER_ALL: function called after each pipeline call
    """

    BEFORE_ALL = auto()
    BEFORE = auto()
    AFTER = auto()
    AFTER_ALL = auto()


@unique
class WrapperStage(Enum):
    """
    Enum, representing wrapper type, pre- or postprocessing.
    The following types are supported:
        PREPROCESSING: wrapper function called before component
        POSTPROCESSING: wrapper function called after component
    """

    UNDEFINED = auto()
    BEFORE = auto()
    AFTER = auto()


"""
PIPELINE: storage for services and groups execution status.
Should be used in `ctx.framework_keys[PIPELINE_STATE_KEY]`.
"""
PIPELINE_STATE_KEY = "PIPELINE"


"""
A function type for messenger_interface-to-client interaction.
Accepts anything (user input) and hashable vaklue (current dialog id), returns string (answer from pipeline).
"""
PipelineRunnerFunction = Callable[[Any, Hashable], Awaitable[Context]]


"""
A function type for components start_conditions.
Accepts context and actor (current pipeline state), returns boolean (whether service can be launched).
"""
StartConditionCheckerFunction = Callable[[Context, Actor], bool]


"""
A function type for creating aggregation start_conditions for components.
Accepts list of functions (other start_conditions to aggregate), returns boolean (whether service can be launched).
"""
StartConditionCheckerAggregationFunction = Callable[[Iterable[bool]], bool]


"""
A function type used during global wrappers initialization to determine
    whether wrapper should be applied to component with given path or not.
Checks components path to be in whitelist (if defined) and not to be in blacklist (if defined).
Accepts str (component path), returns boolean (whether wrapper should be applied).
"""
WrapperConditionFunction = Callable[[str], bool]


"""
A function type used in PollingMessengerInterface to control polling loop.
Returns boolean (whether polling should be continued).
"""
PollingProviderLoopFunction = Callable[[], bool]


"""
Type of dictionary, that is passed to components in runtime.
Contains current component info (`name`, `path`, `timeout`, `asynchronous`).
Also contains `execution_state` - a dictionary,
    containing other pipeline components execution stats mapped to their paths.
"""
ServiceRuntimeInfo = TypedDict(
    "ServiceRuntimeInfo",
    {
        "name": str,
        "path": str,
        "timeout": Optional[int],
        "asynchronous": bool,
        "execution_state": Dict[str, ComponentExecutionState],
    },
)


"""
Type of dictionary, that is passed to wrappers in runtime.
Contains current wrapper info (`name`, `stage`).
Also contains `component` - runtime info dictionary of the component this wrapper is attached to.
"""
WrapperRuntimeInfo = TypedDict(
    "WrapperRuntimeInfo",
    {
        "function": _ForwardWrapperFunction,
        "stage": WrapperStage,
        "component": ServiceRuntimeInfo,
    },
)


"""
A function type for creating wrappers (before and after functions).
Can accept current dialog context, actor, attached to the pipeline, and current wrapper info dictionary.
"""
WrapperFunction = Union[
    Callable[[Context], None],
    Callable[[Context, Actor], None],
    Callable[[Context, Actor, WrapperRuntimeInfo], None],
]


"""
A function type for creating service handlers.
Can accept current dialog context, actor, attached to the pipeline, and current service info dictionary.
Can be both sybchronous and asynchronous.
"""
ServiceFunction = Union[
    Callable[[Context], None],
    Callable[[Context], Awaitable[None]],
    Callable[[Context, Actor], None],
    Callable[[Context, Actor], Awaitable[None]],
    Callable[[Context, Actor, ServiceRuntimeInfo], None],
    Callable[[Context, Actor, ServiceRuntimeInfo], Awaitable[None]],
]


WrapperBuilder = Union[
    _ForwardServiceWrapper,
    TypedDict(
        "WrapperDict",
        {
            "timeout": NotRequired[Optional[int]],
            "asynchronous": NotRequired[bool],
            "functions": List[WrapperFunction],
        },
    ),
    List[WrapperFunction],
]


"""
A type, representing anything that can be transformed to service.
It can be:
    ServiceFunction (will become handler)
    Service object (will be spread and recreated)
    Actor (will be wrapped in a Service as a handler)
    Dictionary, containing keys that are present in Service constructor parameters
"""
ServiceBuilder = Union[
    ServiceFunction,
    _ForwardService,
    Actor,
    TypedDict(
        "ServiceDict",
        {
            "handler": "ServiceBuilder",
            "before_wrapper": NotRequired[Optional[WrapperBuilder]],
            "after_wrapper": NotRequired[Optional[WrapperBuilder]],
            "timeout": NotRequired[Optional[int]],
            "asynchronous": NotRequired[bool],
            "start_condition": NotRequired[StartConditionCheckerFunction],
            "name": Optional[str],
        },
    ),
]


"""
A type, representing anything that can be transformed to service group.
It can be:
    List of ServiceBuilders, ServiceGroup objects and lists (recursive)
    ServiceGroup object (will be spread and recreated)
"""
ServiceGroupBuilder = Union[
    List[Union[ServiceBuilder, List[ServiceBuilder], _ForwardServiceGroup]],
    _ForwardServiceGroup,
]


"""
A type, representing anything that can be transformed to pipeline.
It can be Dictionary, containing keys that are present in Pipeline constructor parameters.
"""
PipelineBuilder = TypedDict(
    "PipelineBuilder",
    {
        "messenger_interface": NotRequired[Optional[_ForwardProvider]],
        "context_storage": NotRequired[Optional[Union[DBAbstractConnector, Dict]]],
        "components": ServiceGroupBuilder,
        "before_wrapper": NotRequired[Optional[WrapperBuilder]],
        "after_wrapper": NotRequired[Optional[WrapperBuilder]],
        "optimization_warnings": NotRequired[bool],
    },
)
