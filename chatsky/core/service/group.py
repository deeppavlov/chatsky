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
from typing import List, Union, Awaitable, TYPE_CHECKING, Any, Optional, Callable

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
from .service import Service

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from chatsky.core.pipeline import Pipeline


class ServiceGroup(PipelineComponent):
    """
    A service group class.
    Service group can be included into pipeline as an object or a pipeline component list.
    Service group can be synchronous or asynchronous.
    Components in synchronous groups are executed consequently (no matter is they are synchronous or asynchronous).
    Components in asynchronous groups are executed simultaneously.
    Group can be asynchronous only if all components in it are asynchronous.
    """

    components: List[
        Union[
            Actor,
            Service,
            ServiceGroup,
        ]
    ]
    """
    A `ServiceGroup` object, that will be added to the group.
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
    def __components_constructor(cls, data: Any):
        if isinstance(data, (list, PipelineComponent, Callable)):
            result = {"components": data}
        elif isinstance(data, dict):
            result = data.copy()
        else:
            raise ValueError(
                "Service Group can only be initialized from a Dict,"
                " a PipelineComponent or a list of PipelineComponents. Wrong inputs received."
            )

        if ("components" in result) and (not isinstance(result["components"], list)):
            result["components"] = [result["components"]]
        return result

    @model_validator(mode="after")
    def __calculate_async_flag(self):
        self.calculated_async_flag = all([service.asynchronous for service in self.components])
        return self

    async def run_component(self, ctx: Context, pipeline: Pipeline) -> Optional[ComponentExecutionState]:
        """
        Method for running this service group. Catches runtime exceptions and logs them.
        It doesn't include extra handlers execution, start condition checking or error handling - pure execution only.
        Executes components inside the group based on its `asynchronous` property.
        Collects information about their execution state - group is finished successfully
        only if all components in it finished successfully.

        :param ctx: Current dialog context.
        :param pipeline: The current pipeline.
        """
        if self.asynchronous:
            service_futures = [service(ctx, pipeline) for service in self.components]
            for service, future in zip(self.components, await asyncio.gather(*service_futures, return_exceptions=True)):
                service_result = future
                if service.asynchronous and isinstance(service_result, Awaitable):
                    await service_result
                elif isinstance(service_result, asyncio.TimeoutError):
                    logger.warning(f"{type(service).__name__} '{service.name}' timed out!")

        else:
            for service in self.components:
                service_result = await service(ctx, pipeline)
                if service.asynchronous and isinstance(service_result, Awaitable):
                    await service_result

        failed = any([service.get_state(ctx) == ComponentExecutionState.FAILED for service in self.components])
        if failed:
            return ComponentExecutionState.FAILED

    def log_optimization_warnings(self):
        """
        Method for logging service group optimization warnings for all this groups inner components.
        (NOT this group itself!).
        Warnings are basically messages,
        that indicate service group inefficiency or explicitly defined parameters mismatch.
        These are cases for warnings issuing:

        - Service can be asynchronous, however is marked synchronous explicitly.
        - Service is not asynchronous, however has a timeout defined.
        - Group is not marked synchronous explicitly and contains both synchronous and asynchronous components.

        :return: `None`
        """
        for service in self.components:
            if not isinstance(service, ServiceGroup):
                if (
                    service.calculated_async_flag
                    and service.requested_async_flag is not None
                    and not service.requested_async_flag
                ):
                    logger.warning(f"Service '{service.name}' could be asynchronous!")
                if not service.asynchronous and service.timeout is not None:
                    logger.warning(f"Timeout can not be applied for Service '{service.name}': it's not asynchronous!")
            else:
                if not service.calculated_async_flag:
                    if service.requested_async_flag is None and any(
                        [sub_service.asynchronous for sub_service in service.components]
                    ):
                        logger.warning(
                            f"ServiceGroup '{service.name}' contains both sync and async services, "
                            "it should be split or marked as synchronous explicitly!",
                        )
                service.log_optimization_warnings()

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
