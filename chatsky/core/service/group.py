"""
Service Group
-------------
The Service Group module contains the ServiceGroup class, which is used to represent a group of related services.

This class provides a way to organize and manage multiple services as a single unit,
allowing for easier management and organization of the services within the pipeline.

:py:class:`~.ServiceGroup` serves the important function of grouping services to work together asynchronously.
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
    GlobalExtraHandlerType,
    ExtraHandlerConditionFunction,
    ExtraHandlerFunction,
)
from .service import Service, ServiceInitTypes

logger = logging.getLogger(__name__)


class ServiceGroup(PipelineComponent):
    """
    A service group class.

    Service group can be synchronous or asynchronous.
    Components in synchronous groups are executed consequently (no matter is they are synchronous or asynchronous).
    Components in asynchronous groups are executed simultaneously.
    Group can be asynchronous only if all components in it are asynchronous.
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
    all_async: bool = False
    """
    Optional flag that, if set to True, makes the `ServiceGroup` run
    all components inside it asynchronously. This is not recursive
    (applies only to first level components). Default value is False.
    """
    # Repeating inherited fields for better documentation.
    before_handler: BeforeHandler = Field(default_factory=BeforeHandler)
    after_handler: AfterHandler = Field(default_factory=AfterHandler)
    timeout: Optional[float] = None
    asynchronous: bool = False
    start_condition: AnyCondition = Field(default=True, validate_default=True)
    name: Optional[str] = None
    path: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def components_validator(cls, data: Any):
        """
        Add support for initializing from a `Callable`, `List`
        and :py:class:`~.PipelineComponent` (such as :py:class:`~.Service`)
        Casts `components` to `list` if it's not already.
        """
        if isinstance(data, list):
            result = {"components": data}
        elif callable(data) or isinstance(data, PipelineComponent):
            result = {"components": [data]}
        else:
            result = data

        if isinstance(result, dict):
            if ("components" in result) and (not isinstance(result["components"], list)):
                result["components"] = [result["components"]]
        return result

    async def run_component(self, ctx: Context) -> Optional[ComponentExecutionState]:
        """
        Method for running this service group. It doesn't include extra handlers execution,
        start condition checking or error handling - pure execution only.
        If this ServiceGroup's `all_async` flag is set to True (it's False by default)
        then all `components` will run simultaneously. Otherwise, ServiceGroup's default logic will apply,
        which is running all sequential components one after another with groups of asynchronous components in between.
        You could say that a group of adjacent 'asynchronous' components is a sequential component itself.
        Collects information about components execution state - group is finished successfully
        only if all components in it finished successfully.

        :param ctx: Current dialog context.
        """
        if self.all_async:
            await asyncio.gather(*[service(ctx) for service in self.components])
        else:
            current_subgroup = []
            for component in self.components:
                if component.asynchronous:
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
        global_extra_handler_type: GlobalExtraHandlerType,
        extra_handler: ExtraHandlerFunction,
        condition: ExtraHandlerConditionFunction = lambda _: False,
    ):
        """
        Method for adding a global extra handler to this group.
        Adds extra handler to itself and propagates it to all inner components.
        Uses a special condition function to determine whether to add extra handler to any particular inner component.
        Condition checks components path to be in whitelist (if defined) and not to be in blacklist (if defined).

        :param global_extra_handler_type: A type of extra handler to add.
        :param extra_handler: A `ExtraHandlerFunction` to add as an extra handler.
        :type extra_handler: :py:data:`~.ExtraHandlerFunction`
        :param condition: A condition function.
        :return: `None`
        """
        super().add_extra_handler(global_extra_handler_type, extra_handler)
        for service in self.components:
            if not condition(service.path):
                continue
            if isinstance(service, ServiceGroup):
                service.add_extra_handler(global_extra_handler_type, extra_handler, condition)
            else:
                service.add_extra_handler(global_extra_handler_type, extra_handler)

    @property
    def computed_name(self) -> str:
        return "service_group"


ServiceGroupInitTypes: TypeAlias = Union[
    ServiceGroup,
    Annotated[List[Union[Actor, ServiceInitTypes, "ServiceGroupInitTypes"]], "list of components"],
    Annotated[Union[Actor, ServiceInitTypes, "ServiceGroupInitTypes"], "single component of the group"],
    Annotated[dict, "dict following the ServiceGroup data model"],
]
"""Types that :py:class:`~.ServiceGroup` can be validated from."""
