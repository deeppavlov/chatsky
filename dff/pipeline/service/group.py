"""
Service Group
-------------
The Service Group module contains the
:py:class:`~.ServiceGroup` class, which is used to represent a group of related services.
This class provides a way to organize and manage multiple services as a single unit,
allowing for easier management and organization of the services within the pipeline.
The :py:class:`~.ServiceGroup` serves the important function of grouping services to work together in parallel.
"""
import asyncio
import logging
from typing import Optional, List, Union, Awaitable, ForwardRef

from dff.script import Context

from .utils import collect_defined_constructor_parameters_to_dict, _get_attrs_with_updates
from ..pipeline.component import PipelineComponent
from ..types import (
    StartConditionCheckerFunction,
    ComponentExecutionState,
    ServiceGroupBuilder,
    GlobalExtraHandlerType,
    ExtraHandlerConditionFunction,
    ExtraHandlerFunction,
    ExtraHandlerBuilder,
    ExtraHandlerType,
)
from .service import Service

logger = logging.getLogger(__name__)

Pipeline = ForwardRef("Pipeline")


class ServiceGroup(PipelineComponent):
    """
    A service group class.
    Service group can be included into pipeline as an object or a pipeline component list.
    Service group can be synchronous or asynchronous.
    Components in synchronous groups are executed consequently (no matter is they are synchronous or asynchronous).
    Components in asynchronous groups are executed simultaneously.
    Group can be asynchronous only if all components in it are asynchronous.
    Group containing actor can be synchronous only.

    :param components: A `ServiceGroupBuilder` object, that will be added to the group.
    :type components: :py:data:`~.ServiceGroupBuilder`
    :param before_handler: List of `ExtraHandlerBuilder` to add to the group.
    :type before_handler: Optional[:py:data:`~.ExtraHandlerBuilder`]
    :param after_handler: List of `ExtraHandlerBuilder` to add to the group.
    :type after_handler: Optional[:py:data:`~.ExtraHandlerBuilder`]
    :param timeout: Timeout to add to the group.
    :param asynchronous: Requested asynchronous property.
    :param start_condition: :py:data:`~.StartConditionCheckerFunction` that is invoked before each group execution;
        group is executed only if it returns `True`.
    :param name: Requested group name.
    """

    def __init__(
        self,
        components: ServiceGroupBuilder,
        before_handler: Optional[ExtraHandlerBuilder] = None,
        after_handler: Optional[ExtraHandlerBuilder] = None,
        timeout: Optional[float] = None,
        asynchronous: Optional[bool] = None,
        start_condition: Optional[StartConditionCheckerFunction] = None,
        name: Optional[str] = None,
    ):
        overridden_parameters = collect_defined_constructor_parameters_to_dict(
            before_handler=before_handler,
            after_handler=after_handler,
            timeout=timeout,
            asynchronous=asynchronous,
            start_condition=start_condition,
            name=name,
        )
        if isinstance(components, ServiceGroup):
            self.__init__(
                **_get_attrs_with_updates(
                    components,
                    (
                        "calculated_async_flag",
                        "path",
                    ),
                    {"requested_async_flag": "asynchronous"},
                    overridden_parameters,
                )
            )
        elif isinstance(components, dict):
            components.update(overridden_parameters)
            self.__init__(**components)
        elif isinstance(components, List):
            self.components = self._create_components(components)
            calc_async = all([service.asynchronous for service in self.components])
            super(ServiceGroup, self).__init__(
                before_handler, after_handler, timeout, asynchronous, calc_async, start_condition, name
            )
        else:
            raise Exception(f"Unknown type for ServiceGroup {components}")

    async def _run_services_group(self, ctx: Context, pipeline: Pipeline) -> Context:
        """
        Method for running this service group.
        It doesn't include wrappers execution, start condition checking or error handling - pure execution only.
        Executes components inside the group based on its `asynchronous` property.
        Collects information about their execution state - group is finished successfully
        only if all components in it finished successfully.

        :param ctx: Current dialog context.
        :param pipeline: The current pipeline.
        :return: Current dialog context.
        """
        self._set_state(ctx, ComponentExecutionState.RUNNING)

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
                if not service.asynchronous and isinstance(service_result, Context):
                    ctx = service_result
                elif service.asynchronous and isinstance(service_result, Awaitable):
                    await service_result

        failed = any([service.get_state(ctx) == ComponentExecutionState.FAILED for service in self.components])
        self._set_state(ctx, ComponentExecutionState.FAILED if failed else ComponentExecutionState.FINISHED)
        return ctx

    async def _run(
        self,
        ctx: Context,
        pipeline: Pipeline = None,
    ) -> Optional[Context]:
        """
        Method for handling this group execution.
        Executes before and after execution wrappers, checks start condition and catches runtime exceptions.

        :param ctx: Current dialog context.
        :param pipeline: The current pipeline.
        :return: Current dialog context if synchronous, else `None`.
        """
        await self.run_extra_handler(ExtraHandlerType.BEFORE, ctx, pipeline)

        try:
            if self.start_condition(ctx, pipeline):
                ctx = await self._run_services_group(ctx, pipeline)
            else:
                self._set_state(ctx, ComponentExecutionState.NOT_RUN)

        except Exception as e:
            self._set_state(ctx, ComponentExecutionState.FAILED)
            logger.error(f"ServiceGroup '{self.name}' execution failed!\n{e}")

        await self.run_extra_handler(ExtraHandlerType.AFTER, ctx, pipeline)
        return ctx if not self.asynchronous else None

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
            if isinstance(service, Service):
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
        condition: ExtraHandlerConditionFunction = lambda _: True,
    ):
        """
        Method for adding a global wrapper to this group.
        Adds wrapper to itself and propagates it to all inner components.
        Uses a special condition function to determine whether to add wrapper to any particular inner component or not.
        Condition checks components path to be in whitelist (if defined) and not to be in blacklist (if defined).

        :param global_extra_handler_type: A type of wrapper to add.
        :param extra_handler: A `WrapperFunction` to add as a wrapper.
        :type extra_handler: :py:data:`~.ExtraHandlerFunction`
        :param condition: A condition function.
        :return: `None`
        """
        super().add_extra_handler(global_extra_handler_type, extra_handler)
        for service in self.components:
            if not condition(service.path):
                continue
            if isinstance(service, Service):
                service.add_extra_handler(global_extra_handler_type, extra_handler)
            else:
                service.add_extra_handler(global_extra_handler_type, extra_handler, condition)

    @property
    def info_dict(self) -> dict:
        """
        See `Component.info_dict` property.
        Adds `services` key to base info dictionary.
        """
        representation = super(ServiceGroup, self).info_dict
        representation.update({"services": [service.info_dict for service in self.components]})
        return representation

    @staticmethod
    def _create_components(services: ServiceGroupBuilder) -> List[Union[Service, "ServiceGroup"]]:
        """
        Utility method, used to create inner components, judging by their nature.
        Services are created from services and dictionaries.
        ServiceGroups are created from service groups and lists.

        :param services: ServiceGroupBuilder object (a `ServiceGroup` instance or a list).
        :type services: :py:data:`~.ServiceGroupBuilder`
        :return: List of services and service groups.
        """
        handled_services: List[Union[Service, "ServiceGroup"]] = []
        for service in services:
            if isinstance(service, List) or isinstance(service, ServiceGroup):
                handled_services.append(ServiceGroup(service))
            else:
                handled_services.append(Service(service))
        return handled_services
