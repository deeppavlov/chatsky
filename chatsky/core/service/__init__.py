"""
Service
-------
This module defines services -- a way to process context outside the Script.
"""

from .component import PipelineComponent
from .extra import BeforeHandler, AfterHandler
from .group import ServiceGroup
from .service import Service, to_service
from .types import (
    ExtraHandlerRuntimeInfo,
    ExtraHandlerType,
    PipelineRunnerFunction,
    ComponentExecutionState,
    ExtraHandlerConditionFunction,
    ExtraHandlerFunction,
)
