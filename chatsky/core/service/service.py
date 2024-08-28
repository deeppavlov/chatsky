"""
Service
-------
The Service module contains the :py:class:`.Service` class which represents a single task.

Pipeline consists of services and service groups.
Service is an atomic part of a pipeline.

Service can be asynchronous only if its handler is a coroutine.
Actor wrapping service is asynchronous.
"""

from __future__ import annotations
import logging
import inspect
from typing import Any, Optional, Callable, Union
from typing_extensions import TypeAlias, Annotated
from pydantic import model_validator, Field

from chatsky.core.context import Context
from chatsky.core.script_function import BaseProcessing
from chatsky.core.service.conditions import always_start_condition
from chatsky.core.service.types import (
    ServiceFunction,
    StartConditionCheckerFunction,
)
from chatsky.core.service.component import PipelineComponent
from .extra import BeforeHandler, AfterHandler

logger = logging.getLogger(__name__)


class Service(PipelineComponent):
    """
    This class represents a service.

    Service can be asynchronous only if its handler is a coroutine.
    """

    handler: BaseProcessing
    """
    A :py:data:`~.ServiceFunction`.
    """
    # Repeating inherited fields for better documentation.
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
            # Rename, if this works at all.
            # What happens when a class is redefined? They'll have the same name,
            # meaning they'll be conflicting, right?
            class PlaceholderClass(BaseProcessing):
                async def call(self, ctx: Context) -> None:
                    data(ctx)

            return {"handler": PlaceholderClass()}
        return data

    async def call(self, ctx: Context) -> None:
        if self.handler is None:
            raise
        await self.handler(ctx)

    async def run_component(self, ctx: Context) -> None:
        """
        Method for running this service.

        :param ctx: Current dialog context.
        :return: `None`
        """
        # Well, ServiceGroup needs a large run_component(), so this is fine.
        await self.handler(ctx)

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
        representation.update({"handler": self.computed_name})
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


ServiceInitTypes: TypeAlias = Union[
    Service, Annotated[dict, "dict following the Service data model"], Annotated[Callable, "handler for the service"]
]
"""Types that :py:class:`~.Service` can be validated from."""
