"""
Service Group
-------------
The Service Group module contains the ServiceGroup class, which is used to represent a group of related services.

This class provides a way to organize and manage multiple services as a single unit,
allowing for easier management and organization of the services within the pipeline.
"""

from __future__ import annotations
import asyncio
import logging
from typing import List, Union, Any, Optional
from typing_extensions import TypeAlias, Annotated

from pydantic import model_validator, Field

from chatsky.core.service.extra import BeforeHandler, AfterHandler
from chatsky.core.script_function import AnyCondition
from chatsky.core.context import Context
from chatsky.core.service.actor import Actor
from chatsky.core.service.component import PipelineComponent
from chatsky.core.service.types import (
    ComponentExecutionState,
    ExtraHandlerType,
    ExtraHandlerConditionFunction,
    ExtraHandlerFunction,
)
from .service import Service, ServiceInitTypes

logger = logging.getLogger(__name__)


class ServiceGroup(PipelineComponent):
    """
    A service group class.
    """

    components: List[
        Union[
            Service,
            ServiceGroup,
        ]
    ]
    """
    A :py:class:`~.ServiceGroup` object, that will be added to the group.
    """
    fully_concurrent: bool = False
    """
    Whether this should run all components inside it concurrently
    (regardless of their `concurrent` attribute.
    This is not recursive (applies only to first level components).
    Default value is False.
    """
    # Repeating inherited fields for better documentation.
    before_handler: BeforeHandler = Field(default_factory=BeforeHandler)
    after_handler: AfterHandler = Field(default_factory=AfterHandler)
    timeout: Optional[float] = None
    concurrent: bool = False
    start_condition: AnyCondition = Field(default=True, validate_default=True)
    name: Optional[str] = None
    path: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def components_validator(cls, data: Any):
        """
        Add support for initializing from a list of :py:class:`~.PipelineComponent`.
        """
        if isinstance(data, list):
            result = {"components": data}
        else:
            result = data

        if isinstance(result, dict):
            if ("components" in result) and (not isinstance(result["components"], list)):
                result["components"] = [result["components"]]
        return result

    async def run_component(self, ctx: Context) -> Optional[ComponentExecutionState]:
        """
        Run components of this service group.

        If :py:attr:`.fully_concurrent` flag is set to True, all :py:attr:`.components` will run concurrently
        (via ``asyncio.gather``).

        Otherwise, all non-concurrent components execute one after another
        while consecutive concurrent components are run concurrently (via ``asyncio.gather``).

        :param ctx: Current dialog context.
        :return: :py:attr:`.ComponentExecutionState.FAILED` if any component failed.
        """
        if self.fully_concurrent:
            await asyncio.gather(*[service(ctx) for service in self.components])
        else:
            current_subgroup = []
            for component in self.components:
                if component.concurrent:
                    current_subgroup.append(component)
                else:
                    await asyncio.gather(*[service(ctx) for service in current_subgroup])
                    await component(ctx)
                    current_subgroup = []
            await asyncio.gather(*[service(ctx) for service in current_subgroup])

        failed = any([service.get_state(ctx) == ComponentExecutionState.FAILED for service in self.components])
        if failed:
            return ComponentExecutionState.FAILED

    def add_extra_handler(
        self,
        extra_handler_type: ExtraHandlerType,
        extra_handler: ExtraHandlerFunction,
        condition: ExtraHandlerConditionFunction = lambda path: False,
    ):
        """
        Add extra handler to this group.

        For every component in the group, ``condition`` is called with the path of that component
        to determine whether to add extra handler to that component.

        :param extra_handler_type: Extra handler type (before or after).
        :param extra_handler: Function to add as an extra handler.
        :type extra_handler: :py:data:`.ExtraHandlerFunction`
        :param condition: Condition function to determine if extra handler should be added to specific subcomponents.
            Defaults to a function returning False.
        :type condition: :py:data:`.ExtraHandlerConditionFunction`
        """
        super().add_extra_handler(extra_handler_type, extra_handler)
        for service in self.components:
            if not condition(service.path):
                continue
            if isinstance(service, ServiceGroup):
                service.add_extra_handler(extra_handler_type, extra_handler, condition)
            else:
                service.add_extra_handler(extra_handler_type, extra_handler)

    @property
    def computed_name(self) -> str:
        """
        "service_group"
        """
        return "service_group"


ServiceGroupInitTypes: TypeAlias = Union[
    ServiceGroup,
    Annotated[List[Union[Actor, ServiceInitTypes, "ServiceGroupInitTypes"]], "list of components"],
    Annotated[Union[Actor, ServiceInitTypes, "ServiceGroupInitTypes"], "single component of the group"],
    Annotated[dict, "dict following the ServiceGroup data model"],
]
"""Types that :py:class:`~.ServiceGroup` can be validated from."""
