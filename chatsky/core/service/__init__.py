"""
Service
-------
This module defines services -- a way to process context outside the Script.
"""

from .component import PipelineComponent
from .conditions import (
    service_successful_condition,
    not_condition,
    all_condition,
    any_condition,
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
    StartConditionCheckerFunction,
    ExtraHandlerConditionFunction,
    ExtraHandlerFunction,
    ServiceFunction,
)
