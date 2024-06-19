"""
Service
-------
The Service module contains the :py:class:`.Service` class,
which can be included into pipeline as object or a dictionary.
Pipeline consists of services and service groups.
Service group can be synchronous or asynchronous.
Service is an atomic part of a pipeline.
Service can be asynchronous only if its handler is a coroutine.
Actor wrapping service is asynchronous.
"""

from __future__ import annotations
import logging
import inspect
from typing import Optional, TYPE_CHECKING

from dff.script import Context

from .utils import wrap_sync_function_in_async, collect_defined_constructor_parameters_to_dict, _get_attrs_with_updates
from ..types import (
    ServiceBuilder,
    StartConditionCheckerFunction,
    ComponentExecutionState,
    ExtraHandlerBuilder,
    ExtraHandlerType,
)
from ..pipeline.component import PipelineComponent

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dff.pipeline.pipeline.pipeline import Pipeline


class Service(PipelineComponent):
    """
    This class represents a service.
    Service can be included into pipeline as object or a dictionary.
    Service group can be synchronous or asynchronous.
    Service can be asynchronous only if its handler is a coroutine.

    :param handler: A service function or an actor.
    :type handler: :py:data:`~.ServiceBuilder`
    :param before_handler: List of `ExtraHandlerBuilder` to add to the group.
    :type before_handler: Optional[:py:data:`~.ExtraHandlerBuilder`]
    :param after_handler: List of `ExtraHandlerBuilder` to add to the group.
    :type after_handler: Optional[:py:data:`~.ExtraHandlerBuilder`]
    :param timeout: Timeout to add to the group.
    :param asynchronous: Requested asynchronous property.
    :param start_condition: StartConditionCheckerFunction that is invoked before each service execution;
        service is executed only if it returns `True`.
    :type start_condition: Optional[:py:data:`~.StartConditionCheckerFunction`]
    :param name: Requested service name.
    """

    def __init__(
        self,
        handler: ServiceBuilder,
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
        if isinstance(handler, dict):
            handler.update(overridden_parameters)
            self.__init__(**handler)
        elif isinstance(handler, Service):
            self.__init__(
                **_get_attrs_with_updates(
                    handler,
                    (
                        "calculated_async_flag",
                        "path",
                    ),
                    {"requested_async_flag": "asynchronous"},
                    overridden_parameters,
                )
            )
        elif callable(handler) or isinstance(handler, str) and handler == "ACTOR":
            self.handler = handler
            super(Service, self).__init__(
                before_handler,
                after_handler,
                timeout,
                True,
                True,
                start_condition,
                name,
            )
        else:
            raise Exception(f"Unknown type of service handler: {handler}")

    async def _run_handler(self, ctx: Context, pipeline: Pipeline) -> None:
        """
        Method for service `handler` execution.
        Handler has three possible signatures, so this method picks the right one to invoke.
        These possible signatures are:

        - (ctx: Context) - accepts current dialog context only.
        - (ctx: Context, pipeline: Pipeline) - accepts context and current pipeline.
        - | (ctx: Context, pipeline: Pipeline, info: ServiceRuntimeInfo) - accepts context,
              pipeline and service runtime info dictionary.

        :param ctx: Current dialog context.
        :param pipeline: The current pipeline.
        :return: `None`
        """
        handler_params = len(inspect.signature(self.handler).parameters)
        if handler_params == 1:
            await wrap_sync_function_in_async(self.handler, ctx)
        elif handler_params == 2:
            await wrap_sync_function_in_async(self.handler, ctx, pipeline)
        elif handler_params == 3:
            await wrap_sync_function_in_async(self.handler, ctx, pipeline, self._get_runtime_info(ctx))
        else:
            raise Exception(f"Too many parameters required for service '{self.name}' handler: {handler_params}!")

    async def _run_as_actor(self, ctx: Context, pipeline: Pipeline) -> None:
        """
        Method for running this service if its handler is an `Actor`.
        Catches runtime exceptions.

        :param ctx: Current dialog context.
        """
        try:
            await pipeline.actor(pipeline, ctx)
            self._set_state(ctx, ComponentExecutionState.FINISHED)
        except Exception as exc:
            self._set_state(ctx, ComponentExecutionState.FAILED)
            logger.error(f"Actor '{self.name}' execution failed!", exc_info=exc)

    async def _run_as_service(self, ctx: Context, pipeline: Pipeline) -> None:
        """
        Method for running this service if its handler is not an Actor.
        Checks start condition and catches runtime exceptions.

        :param ctx: Current dialog context.
        :param pipeline: Current pipeline.
        """
        try:
            if self.start_condition(ctx, pipeline):
                self._set_state(ctx, ComponentExecutionState.RUNNING)
                await self._run_handler(ctx, pipeline)
                self._set_state(ctx, ComponentExecutionState.FINISHED)
            else:
                self._set_state(ctx, ComponentExecutionState.NOT_RUN)
        except Exception as exc:
            self._set_state(ctx, ComponentExecutionState.FAILED)
            logger.error(f"Service '{self.name}' execution failed!", exc_info=exc)

    async def _run(self, ctx: Context, pipeline: Pipeline) -> None:
        """
        Method for handling this service execution.
        Executes extra handlers before and after execution, launches `_run_as_actor` or `_run_as_service` method.

        :param ctx: (required) Current dialog context.
        :param pipeline: the current pipeline.
        """
        await self.run_extra_handler(ExtraHandlerType.BEFORE, ctx, pipeline)

        if isinstance(self.handler, str) and self.handler == "ACTOR":
            await self._run_as_actor(ctx, pipeline)
        else:
            await self._run_as_service(ctx, pipeline)

        await self.run_extra_handler(ExtraHandlerType.AFTER, ctx, pipeline)

    @property
    def info_dict(self) -> dict:
        """
        See `Component.info_dict` property.
        Adds `handler` key to base info dictionary.
        """
        representation = super(Service, self).info_dict
        if isinstance(self.handler, str) and self.handler == "ACTOR":
            service_representation = "Instance of Actor"
        elif callable(self.handler):
            service_representation = f"Callable '{self.handler.__name__}'"
        else:
            service_representation = "[Unknown]"
        representation.update({"handler": service_representation})
        return representation


def to_service(
    before_handler: Optional[ExtraHandlerBuilder] = None,
    after_handler: Optional[ExtraHandlerBuilder] = None,
    timeout: Optional[int] = None,
    asynchronous: Optional[bool] = None,
    start_condition: Optional[StartConditionCheckerFunction] = None,
    name: Optional[str] = None,
):
    """
    Function for decorating a function as a Service.
    Returns a Service, constructed from this function (taken as a handler).
    All arguments are passed directly to `Service` constructor.
    """

    def inner(handler: ServiceBuilder) -> Service:
        return Service(
            handler=handler,
            before_handler=before_handler,
            after_handler=after_handler,
            timeout=timeout,
            asynchronous=asynchronous,
            start_condition=start_condition,
            name=name,
        )

    return inner
