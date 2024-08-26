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
from pydantic import model_validator, Field

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
    """

    handler: ServiceFunction
    """
    A :py:data:`~.ServiceFunction`.
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
    def handler_validator(cls, data: Any):
        """
        Add support for initializing from a `Callable`.
        """
        if isinstance(data, Callable):
            return {"handler": data}
        return data

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
        if inspect.isfunction(self.handler):
            return self.handler.__name__
        else:
            return self.handler.__class__.__name__

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
    asynchronous: bool = False,
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
            asynchronous=asynchronous,
            start_condition=start_condition,
            name=name,
        )

    return inner
