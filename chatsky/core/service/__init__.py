"""
Service
-------
This module defines services -- a way to process context outside the Script.
"""

from .component import PipelineComponent
from .conditions import (
    ServiceFinishedCondition,
)
from .extra import BeforeHandler, AfterHandler
from .group import ServiceGroup
from .service import Service, to_service
from .types import (
    ServiceRuntimeInfo,
    ExtraHandlerRuntimeInfo,
    GlobalExtraHandlerType,
    ExtraHandlerType,
    PipelineRunnerFunction,
    ComponentExecutionState,
    ExtraHandlerConditionFunction,
    ExtraHandlerFunction,
    ServiceFunction,
)
