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
from typing import TYPE_CHECKING, Any
from pydantic import model_validator

from chatsky.script import Context


from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from ..types import (
    ServiceFunction,
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
    :param requested_async_flag: Requested asynchronous property.
    :param start_condition: StartConditionCheckerFunction that is invoked before each service execution;
        service is executed only if it returns `True`.
    :type start_condition: Optional[:py:data:`~.StartConditionCheckerFunction`]
    :param name: Requested service name.
    """

    handler: ServiceFunction

    # This code handles cases where just one Callable is passed into it's constructor data.
    # All flags will be on default in that case.
    @model_validator(mode="before")
    @classmethod
    # Here Script class has "@validate_call". Is it needed here?
    def handler_constructor(cls, data: Any):
        if not isinstance(data, dict):
            return {"handler": data}
        return data

    @model_validator(mode="after")
    def tick_async_flag(self):
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
