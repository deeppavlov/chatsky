import logging
import asyncio
import inspect
from typing import Optional, Callable

from dff.core.engine.core import Actor, Context

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


class Service(PipelineComponent):
    """
    This class represents a service.
    Service can be included into pipeline as object or a dictionary.
    Service group can be synchronous or asynchronous.
    Service can be asynchronous only if its handler is a coroutine.
    Actor wrapping service can be synchronous only.
    It accepts constructor parameters:

    :param handler: a service function or an actor
    :param wrappers: list of Wrappers to add to the service
    :param timeout: timeout to add to the group
    :param asynchronous: requested asynchronous property
    :param start_condition: StartConditionCheckerFunction that is invoked before each service execution;
        service is executed only if it returns True
    :param name: requested service name
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
        elif isinstance(handler, Callable):
            self.handler = handler
            super(Service, self).__init__(
                before_handler,
                after_handler,
                timeout,
                asynchronous,
                asyncio.iscoroutinefunction(handler),
                start_condition,
                name,
            )
        else:
            raise Exception(f"Unknown type of service handler: {handler}")

    async def _run_handler(self, ctx: Context, actor: Actor):
        """
        Method for service `handler` execution.
        Handler has three possible signatures, so this method picks the right one to invoke.
        These possible signatures are:

            - (ctx: Context) - accepts current dialog context only
            - (ctx: Context, actor: Actor) - accepts context and actor, associated with the pipeline
            - (ctx: Context, actor: Actor, info: ServiceRuntimeInfo) - accepts context,
              actor and service runtime info dictionary.

        :param ctx: - current dialog context only.
        :param actor: - actor, associated with the pipeline.
        :return: None
        """
        handler_params = len(inspect.signature(self.handler).parameters)
        if handler_params == 1:
            await wrap_sync_function_in_async(self.handler, ctx)
        elif handler_params == 2:
            await wrap_sync_function_in_async(self.handler, ctx, actor)
        elif handler_params == 3:
            await wrap_sync_function_in_async(self.handler, ctx, actor, self._get_runtime_info(ctx))
        else:
            raise Exception(f"Too many parameters required for service '{self.name}' handler: {handler_params}!")

    def _run_as_actor(self, ctx: Context):
        """
        Method for running this service if its handler is an Actor.
        Catches runtime exceptions.

        :param ctx: current dialog context.
        :return: context, mutated by actor.
        """
        try:
            ctx = self.handler(ctx)
            self._set_state(ctx, ComponentExecutionState.FINISHED)
        except Exception as exc:
            self._set_state(ctx, ComponentExecutionState.FAILED)
            logger.error(f"Actor '{self.name}' execution failed!\n{exc}")
        return ctx

    async def _run_as_service(self, ctx: Context, actor: Actor):
        """
        Method for running this service if its handler is not an Actor.
        Checks start condition and catches runtime exceptions.

        :param ctx: current dialog context.
        :param actor: current pipeline's actor.
        :return: None
        """
        try:
            if self.start_condition(ctx, actor):
                self._set_state(ctx, ComponentExecutionState.RUNNING)
                await self._run_handler(ctx, actor)
                self._set_state(ctx, ComponentExecutionState.FINISHED)
            else:
                self._set_state(ctx, ComponentExecutionState.NOT_RUN)
        except Exception as e:
            self._set_state(ctx, ComponentExecutionState.FAILED)
            logger.error(f"Service '{self.name}' execution failed!\n{e}")

    async def _run(self, ctx: Context, actor: Optional[Actor] = None) -> Optional[Context]:
        """
        Method for handling this service execution.
        Executes before and after execution wrappers, launches `_run_as_actor` or `_run_as_service` method.

        :param ctx: (required) current dialog context.
        :param actor: actor, associated with the pipeline.
        :return: context if this service's handler is an Actor else None.
        """
        await self.run_extra_handler(ExtraHandlerType.BEFORE, ctx, actor)

        if isinstance(self.handler, Actor):
            ctx = self._run_as_actor(ctx)
        else:
            await self._run_as_service(ctx, actor)

        await self.run_extra_handler(ExtraHandlerType.AFTER, ctx, actor)

        if isinstance(self.handler, Actor):
            return ctx

    @property
    def info_dict(self) -> dict:
        """
        See `Component.info_dict` property.
        Adds `handler` key to base info dictionary.
        """
        representation = super(Service, self).info_dict
        if isinstance(self.handler, Actor):
            service_representation = f"Instance of {type(self.handler).__name__}"
        elif isinstance(self.handler, Callable):
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
    All arguments are passed directly to Service constructor.
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
