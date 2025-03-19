"""
Service
-------
The Service module contains the :py:class:`.Service` class which represents a single task.

Pipeline consists of services and service groups.
Service is an atomic part of a pipeline.
"""

from __future__ import annotations
import logging
import inspect
from typing import Any, Optional, Callable, Union
from typing_extensions import TypeAlias, Annotated
from pydantic import model_validator, Field

from chatsky.core.context import Context
from chatsky.core.script_function import BaseProcessing, AnyCondition
from chatsky.core.service.component import PipelineComponent
from .extra import BeforeHandler, AfterHandler
from chatsky.utils.devel import wrap_sync_function_in_async

logger = logging.getLogger(__name__)


class Service(PipelineComponent):
    """
    This class represents a service.
    """

    handler: Union[BaseProcessing, Callable[[Context], None]] = None
    """
    Function that represents this service.
    """
    # Repeating inherited fields for better documentation.
    before_handler: BeforeHandler = Field(default_factory=BeforeHandler)
    after_handler: AfterHandler = Field(default_factory=AfterHandler)
    timeout: Optional[float] = None
    concurrent: bool = False
    start_condition: AnyCondition = Field(default=True, validate_default=True)
    name: Optional[str] = None
    path: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def handler_validator(cls, data: Any):
        """
        Add support for initializing from a `Callable` or `BaseProcessing`.
        """
        if inspect.isfunction(data) or isinstance(data, BaseProcessing):
            return {"handler": data}
        return data

    async def call(self, ctx: Context) -> None:
        """
        A placeholder method which the user can redefine in their own derivative of :py:class:`.Service`.
        This allows direct access to the ``self`` object and all its fields.

        :param ctx: Current dialog context.
        """
        if self.handler is None:
            raise NotImplementedError(
                f"Received {self.__class__.__name__} object, which has it's 'handler' == 'None',"
                f" while also not defining it's own 'call()' method."
            )
        await wrap_sync_function_in_async(self.handler, ctx)

    async def run_component(self, ctx: Context) -> None:
        """
        Method for running this service.

        :param ctx: Current dialog context.
        :return: `None`
        """
        await wrap_sync_function_in_async(self.call, ctx)

    @property
    def computed_name(self) -> str:
        """
        Return name of the handler or name of this class if handler is empty.
        """
        if inspect.isfunction(self.handler):
            return self.handler.__name__
        elif self.handler is None:
            return self.__class__.__name__
        else:
            return self.handler.__class__.__name__


def to_service(
    before_handler: BeforeHandler = None,
    after_handler: AfterHandler = None,
    timeout: Optional[int] = None,
    concurrent: bool = False,
    start_condition: AnyCondition = True,
    name: Optional[str] = None,
):
    """
    Return a function decorator that returns a :py:class:`Service` with the
    given parameters.
    """
    before_handler = BeforeHandler() if before_handler is None else before_handler
    after_handler = AfterHandler() if after_handler is None else after_handler

    def inner(handler: Union[BaseProcessing, Callable]) -> Service:
        return Service(
            handler=handler,
            before_handler=before_handler,
            after_handler=after_handler,
            timeout=timeout,
            concurrent=concurrent,
            start_condition=start_condition,
            name=name,
        )

    return inner


ServiceInitTypes: TypeAlias = Union[
    Service,
    Annotated[dict, "dict following the Service data model"],
    Annotated[Callable, "handler for the service"],
    Annotated[BaseProcessing, "handler for the service"],
]
"""Types that :py:class:`~.Service` can be validated from."""
