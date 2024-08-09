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
from typing import TYPE_CHECKING, Any, Optional, Callable
from pydantic import model_validator

from chatsky.script import Context


from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from chatsky.pipeline import always_start_condition
from ..types import (
    ServiceFunction,
    StartConditionCheckerFunction,
)
from ..pipeline.component import PipelineComponent
from .extra import BeforeHandler, AfterHandler

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from chatsky.pipeline.pipeline.pipeline import Pipeline


class Service(PipelineComponent):
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
    :param requested_async_flag: Requested asynchronous property.
    :param start_condition: StartConditionCheckerFunction that is invoked before each service execution;
        service is executed only if it returns `True`.
    :type start_condition: Optional[:py:data:`~.StartConditionCheckerFunction`]
    :param name: Requested service name.
    """

    handler: ServiceFunction

    @model_validator(mode="before")
    @classmethod
    def __handler_constructor(cls, data: Any):
        if isinstance(data, Callable):
            return {"handler": data}
        elif not isinstance(data, dict):
            raise ValueError("A Service can only be initialized from a Dict or a Callable." " Wrong inputs received.")
        return data

    @model_validator(mode="after")
    def __tick_async_flag(self):
        self.calculated_async_flag = True
        return self

    async def run_component(self, ctx: Context, pipeline: Pipeline) -> None:
        """
        Method for running this service. Service 'handler' has three possible signatures,
        so this method picks the right one to invoke. These possible signatures are:

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

    @property
    def computed_name(self) -> str:
        if callable(self.handler):
            if inspect.isfunction(self.handler):
                return self.handler.__name__
            else:
                return self.handler.__class__.__name__
        else:
            return "noname_service"

    @property
    def info_dict(self) -> dict:
        """
        See `Component.info_dict` property.
        Adds `handler` key to base info dictionary.
        """
        representation = super(Service, self).info_dict
        # Need to carefully remove this
        if callable(self.handler):
            service_representation = f"Callable '{self.handler.__name__}'"
        else:
            service_representation = "[Unknown]"
        representation.update({"handler": service_representation})
        return representation


def to_service(
    before_handler: BeforeHandler = None,
    after_handler: AfterHandler = None,
    timeout: Optional[int] = None,
    asynchronous: Optional[bool] = None,
    start_condition: StartConditionCheckerFunction = always_start_condition,
    name: Optional[str] = None,
):
    """
    Function for decorating a function as a Service.
    Returns a Service, constructed from this function (taken as a handler).
    All arguments are passed directly to `Service` constructor.
    """
    before_handler = BeforeHandler() if before_handler is None else before_handler
    after_handler = AfterHandler() if after_handler is None else after_handler

    def inner(handler: ServiceFunction) -> Service:
        return Service(
            handler=handler,
            before_handler=before_handler,
            after_handler=after_handler,
            timeout=timeout,
            requested_async_flag=asynchronous,
            start_condition=start_condition,
            name=name,
        )

    return inner
