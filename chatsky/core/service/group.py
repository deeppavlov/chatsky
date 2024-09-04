"""
Service Group
-------------
The Service Group module contains the ServiceGroup class, which is used to represent a group of related services.

This class provides a way to organize and manage multiple services as a single unit,
allowing for easier management and organization of the services within the pipeline.

:py:class:`~.ServiceGroup` serves the important function of grouping services to work together in parallel.
"""

from __future__ import annotations
import asyncio
import logging
from typing import List, Union, Awaitable, TYPE_CHECKING, Any, Optional
from typing_extensions import TypeAlias, Annotated

from pydantic import model_validator, Field

from chatsky.core.service.extra import BeforeHandler, AfterHandler
from chatsky.core.service.conditions import always_start_condition
from chatsky.core.context import Context
from chatsky.core.service.actor import Actor
from chatsky.core.service.component import PipelineComponent
from chatsky.core.service.types import (
    ComponentExecutionState,
    GlobalExtraHandlerType,
    ExtraHandlerConditionFunction,
    ExtraHandlerFunction,
    StartConditionCheckerFunction,
)
from .service import Service, ServiceInitTypes

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from chatsky.core.pipeline import Pipeline


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
    all components inside it asynchronously. Default value is False.
    """
    # Inherited fields repeated. Don't delete these, they're needed for documentation!
    before_handler: BeforeHandler = Field(default_factory=BeforeHandler)
    after_handler: AfterHandler = Field(default_factory=AfterHandler)
    timeout: Optional[float] = None
    requested_async_flag: Optional[bool] = None
    start_condition: StartConditionCheckerFunction = Field(default=always_start_condition)
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

    async def _run_async_components(self, ctx: Context, pipeline: Pipeline, components: List) -> None:
        """
        Method for running a group of asynchronous components in parallel to each other.
        No check if they are asynchronous or not happens.

        :param ctx: Current dialog context.
        :param pipeline: The current pipeline.
        :param components: The components to run in parallel to each other.
        """
        service_futures = [service(ctx, pipeline) for service in components]
        for service, future in zip(components, await asyncio.gather(*service_futures, return_exceptions=True)):
            service_result = future
            if service.asynchronous and isinstance(service_result, Awaitable):
                await service_result
            elif isinstance(service_result, asyncio.TimeoutError):
                logger.warning(f"{type(service).__name__} '{service.name}' timed out!")

    async def _run_sync_component(self, ctx: Context, pipeline: Pipeline, component: Any) -> None:
        """
        Method for running a single synchronous component.

        :param ctx: Current dialog context.
        :param pipeline: The current pipeline.
        :param component: The component be run.
        """
        service_result = await component(ctx, pipeline)
        if component.asynchronous and isinstance(service_result, Awaitable):
            await service_result

    async def run_component(self, ctx: Context, pipeline: Pipeline) -> Optional[ComponentExecutionState]:
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
        :param pipeline: The current pipeline.
        """
        if self.all_async:
            await self._run_async_components(ctx, pipeline, self.components)
        else:
            current_subgroup = []
            for component in self.components:
                if component.asynchronous:
                    current_subgroup.append(component)
                else:
                    await self._run_async_components(ctx, pipeline, current_subgroup)
                    await self._run_sync_component(ctx, pipeline, component)
                    current_subgroup = []
            await self._run_async_components(ctx, pipeline, current_subgroup)

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

    @property
    def info_dict(self) -> dict:
        """
        See `Component.info_dict` property.
        Adds `services` key to base info dictionary.
        """
        representation = super(ServiceGroup, self).info_dict
        representation.update({"services": [service.info_dict for service in self.components]})
        return representation


ServiceGroupInitTypes: TypeAlias = Union[
    ServiceGroup,
    Annotated[List[Union[Actor, ServiceInitTypes, "ServiceGroupInitTypes"]], "list of components"],
    Annotated[Union[Actor, ServiceInitTypes, "ServiceGroupInitTypes"], "single component of the group"],
    Annotated[dict, "dict following the ServiceGroup data model"],
]
"""Types that :py:class:`~.ServiceGroup` can be validated from."""
