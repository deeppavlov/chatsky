"""
Service Group
-------------
The Service Group module contains the
:py:class:`~.ServiceGroup` class, which is used to represent a group of related services.
This class provides a way to organize and manage multiple services as a single unit,
allowing for easier management and organization of the services within the pipeline.
The :py:class:`~.ServiceGroup` serves the important function of grouping services to work together in parallel.
"""

from __future__ import annotations
import asyncio
import logging
from typing import List, Union, Awaitable, TYPE_CHECKING, Any
from pydantic import model_validator

from chatsky.script import Context
from ..pipeline.actor import Actor

from ..pipeline.component import PipelineComponent
from ..types import (
    ComponentExecutionState,
    GlobalExtraHandlerType,
    ExtraHandlerConditionFunction,
    ExtraHandlerFunction,
)
from .service import Service

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from chatsky.pipeline.pipeline.pipeline import Pipeline


class ServiceGroup(PipelineComponent, extra="forbid", arbitrary_types_allowed=True):
    """
    A service group class.
    Service group can be included into pipeline as an object or a pipeline component list.
    Service group can be synchronous or asynchronous.
    Components in synchronous groups are executed consequently (no matter is they are synchronous or asynchronous).
    Components in asynchronous groups are executed simultaneously.
    Group can be asynchronous only if all components in it are asynchronous.

    :param components: A `ServiceGroup` object, that will be added to the group.
    :type components: :py:data:`~.ServiceGroup`
    :param before_handler: List of `_ComponentExtraHandler` to add to the group.
    :type before_handler: Optional[:py:data:`~._ComponentExtraHandler`]
    :param after_handler: List of `_ComponentExtraHandler` to add to the group.
    :type after_handler: Optional[:py:data:`~._ComponentExtraHandler`]
    :param timeout: Timeout to add to the group.
    :param asynchronous: Optional flag that indicates whether the components inside
        should be executed concurrently. The default value of the flag is False.
    :param all_async: Optional flag that, if set to True, makes the `ServiceGroup` run
        all components inside it asynchronously. Default value is False.
    :param start_condition: :py:data:`~.StartConditionCheckerFunction` that is invoked before each group execution;
        group is executed only if it returns `True`.
    :param name: Requested group name.
    """

    components: List[
        Union[
            Actor,
            Service,
            ServiceGroup,
        ]
    ]
    all_async: bool = False

    @model_validator(mode="before")
    @classmethod
    # Here Script class has "@validate_call". Is it needed here?
    def components_constructor(cls, data: Any):
        if not isinstance(data, dict):
            result = {"components": data}
        else:
            result = data.copy()

        if ("components" in result) and (not isinstance(result["components"], list)):
            result["components"] = [result["components"]]
        return result

    async def _run_async_components(self, ctx: Context, pipeline: Pipeline, components: List) -> None:
        service_futures = [service(ctx, pipeline) for service in components]
        for service, future in zip(components, await asyncio.gather(*service_futures, return_exceptions=True)):
            service_result = future
            if service.asynchronous and isinstance(service_result, Awaitable):
                await service_result
            elif isinstance(service_result, asyncio.TimeoutError):
                logger.warning(f"{type(service).__name__} '{service.name}' timed out!")

    async def _run_sync_component(self, ctx: Context, pipeline: Pipeline, component: Any) -> None:
        service_result = await component(ctx, pipeline)
        if component.asynchronous and isinstance(service_result, Awaitable):
            await service_result

    async def run_component(self, ctx: Context, pipeline: Pipeline) -> None:
        """
        Method for running this service group. It doesn't include extra handlers execution,
        start condition checking or error handling - pure execution only.
        If this ServiceGroup's `all_async` flag is set to True (it's False by default)
        then all `components` will run simultaneously. Otherwise ServiceGroup's default logic will apply,
        which is running all sequential components one after another with groups of asynchronous components in between.
        You could say that a group of adjacent 'asynchronous' components is a sequential component itself.
        Collects information about components execution state - group is finished successfully
        only if all components in it finished successfully.

        :param ctx: Current dialog context.
        :param pipeline: The current pipeline.
        """
        if self.all_async:
            await self._run_sync_component(ctx, pipeline, self.components)
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
        self._set_state(ctx, ComponentExecutionState.FAILED if failed else ComponentExecutionState.FINISHED)

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
    def info_dict(self) -> dict:
        """
        See `Component.info_dict` property.
        Adds `services` key to base info dictionary.
        """
        representation = super(ServiceGroup, self).info_dict
        representation.update({"services": [service.info_dict for service in self.components]})
        return representation
