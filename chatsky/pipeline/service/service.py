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
from typing import Optional, TYPE_CHECKING, Union, List

from chatsky.script import Context


from .extra import ComponentExtraHandler
from .utils import collect_defined_constructor_parameters_to_dict, _get_attrs_with_updates
from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from ..types import (
    ServiceBuilder,
    StartConditionCheckerFunction,
    ComponentExecutionState,
    ExtraHandlerType,
)
from ..pipeline.component import PipelineComponent

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from chatsky.pipeline.pipeline.pipeline import Pipeline


# arbitrary_types_allowed for testing, will remove later
class Service(PipelineComponent, extra="forbid", arbitrary_types_allowed=True):
    """
    This class represents a service.
    Service can be included into pipeline as object or a dictionary.
    Service group can be synchronous or asynchronous.
    Service can be asynchronous only if its handler is a coroutine.

    :param handler: A service function or an actor.
    :type handler: :py:data:`~.ServiceFunction`
    :param before_handler: List of `_ComponentExtraHandler` to add to the group.
    :type before_handler: Optional[:py:data:`~._ComponentExtraHandler`]
    :param after_handler: List of `_ComponentExtraHandler` to add to the group.
    :type after_handler: Optional[:py:data:`~._ComponentExtraHandler`]
    :param timeout: Timeout to add to the group.
    :param asynchronous: Requested asynchronous property.
    :param start_condition: StartConditionCheckerFunction that is invoked before each service execution;
        service is executed only if it returns `True`.
    :type start_condition: Optional[:py:data:`~.StartConditionCheckerFunction`]
    :param name: Requested service name.
    """

    handler: ServiceFunction
    # Should these be removed from the above API reference? I think they're still useful for users if included in API reference.
    # before_handler: Optional[ComponentExtraHandler] = None
    # after_handler: Optional[ComponentExtraHandler] = None
    # timeout: Optional[float] = None
    # asynchronous: Optional[bool] = None
    calculated_async_flag: Optional[bool] = True
    # start_condition: Optional[StartConditionCheckerFunction] = None
    # name: Optional[str] = None

    @model_validator(mode="after")
    def tick_async_flag(self):
        self.calculated_async_flag = True

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

    async def run_component(self, ctx: Context, pipeline: Pipeline) -> None:
        """
        Method for running this service.
        Catches runtime exceptions and logs them.

        :param ctx: Current dialog context.
        :param pipeline: Current pipeline.
        """
        try:
            await self._run_handler(ctx, pipeline)
        except Exception as exc:
            self._set_state(ctx, ComponentExecutionState.FAILED)
            logger.error(f"Service '{self.name}' execution failed!", exc_info=exc)

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
