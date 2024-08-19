"""
Script Function
---------------
This module provides base classes for functions used in :py:class:`~chatsky.core.script.Script` instances.

These functions allow dynamic script configuration and are essential to the scripting process.
"""
from __future__ import annotations

from types import NoneType
from typing import Generic, TypeVar, Union, Tuple, ClassVar, Optional, Annotated, Any
from abc import abstractmethod, ABC
import logging

from pydantic import BaseModel, model_validator, Field

from chatsky.utils.devel import wrap_sync_function_in_async
from chatsky.core.context import Context
from chatsky.core.message import Message, MessageInitTypes
from chatsky.core.node_label import NodeLabel, NodeLabelInitTypes, AbsoluteNodeLabel


logger = logging.getLogger(__name__)


ReturnType = TypeVar("ReturnType")


class BaseScriptFunc(BaseModel, ABC, frozen=True):
    """
    Base class for any script function.

    Defines :py:meth:`wrapped_call` that wraps :py:meth:`call` and handles exceptions and types conversions.
    """
    return_type: ClassVar[Union[type, Tuple[type, ...]]]
    """Return type of the script function."""

    @abstractmethod
    async def call(self, ctx: Context):
        """Implement this to create a custom function."""
        raise NotImplementedError()

    async def wrapped_call(self, ctx: Context, info: str = ""):
        """
        Handle :py:meth:`call`:

        - Call it (regardless of whether it is async);
        - Cast returned value to :py:attr:`return_type`;
        - Catch exceptions.

        :return: An instance of :py:attr:`return_type` if possible.
            Otherwise, an ``Exception`` instance detailing what went wrong.
        """
        try:
            result = await wrap_sync_function_in_async(self.call, ctx)
            if not isinstance(self.return_type, tuple) and issubclass(self.return_type, BaseModel):
                result = self.return_type.model_validate(result, context={"ctx": ctx})
            if not isinstance(result, self.return_type):
                raise TypeError(
                    f"Function `call` of {self.__class__.__name__} should return {self.return_type!r}. "
                    f"Got instead: {result!r}"
                )
            logger.debug(f"Function {self.__class__.__name__} returned {result!r}. {info}")
            return result
        except Exception as exc:
            logger.warning(f"An exception occurred in {self.__class__.__name__}. {info}", exc_info=exc)
            return exc

    async def __call__(self, ctx: Context, info: str = ""):
        return await self.wrapped_call(ctx, info)


class ConstScriptFunc(BaseScriptFunc):
    """
    Base class for script functions that return a constant value.
    """
    root: None
    """Value to return."""

    async def call(self, ctx: Context):
        return self.root

    @model_validator(mode="before")
    @classmethod
    def validate_value(cls, data):
        """Allow instantiating this class from its root value."""
        return {"root": data}


class BaseCondition(BaseScriptFunc, ABC):
    """
    Base class for condition functions.

    These are used in :py:attr:`chatsky.core.transition.Transition.cnd`.
    """
    return_type: ClassVar[Union[type, Tuple[type, ...]]] = bool

    @abstractmethod
    async def call(self, ctx: Context) -> bool:
        raise NotImplementedError

    async def __call__(self, ctx: Context, info: str = "") -> bool:
        result = await self.wrapped_call(ctx, info)
        if not isinstance(result, bool):
            return False
        return result


class ConstCondition(ConstScriptFunc, BaseCondition):
    root: bool


AnyCondition = Annotated[Union[ConstCondition, BaseCondition], Field(union_mode="left_to_right")]
"""
A type annotation that allows accepting both :py:class:`ConstCondition` and :py:class:`BaseCondition`
while validating :py:class:`ConstCondition` if possible.
"""


class BaseResponse(BaseScriptFunc, ABC):
    """
    Base class for response functions.

    These are used in :py:attr:`chatsky.core.script.Node.response`.
    """
    return_type: ClassVar[Union[type, Tuple[type, ...]]] = Message

    @abstractmethod
    async def call(self, ctx: Context) -> MessageInitTypes:
        raise NotImplementedError


class ConstResponse(ConstScriptFunc, BaseResponse):
    root: Message


AnyResponse = Annotated[Union[ConstResponse, BaseResponse], Field(union_mode="left_to_right")]
"""
A type annotation that allows accepting both :py:class:`ConstResponse` and :py:class:`BaseResponse`
while validating :py:class:`ConstResponse` if possible.
"""


class BaseDestination(BaseScriptFunc, ABC):
    """
    Base class for destination functions.

    These are used in :py:attr:`chatsky.core.transition.Transition.dst`.
    """
    return_type: ClassVar[Union[type, Tuple[type, ...]]] = AbsoluteNodeLabel

    @abstractmethod
    async def call(self, ctx: Context) -> NodeLabelInitTypes:
        raise NotImplementedError


class ConstDestination(ConstScriptFunc, BaseDestination):
    root: NodeLabel


AnyDestination = Annotated[Union[ConstDestination, BaseDestination], Field(union_mode="left_to_right")]
"""
A type annotation that allows accepting both :py:class:`ConstDestination` and :py:class:`BaseDestination`
while validating :py:class:`ConstDestination` if possible.
"""


class BaseProcessing(BaseScriptFunc, ABC):
    """
    Base class for processing functions.

    These are used in :py:attr:`chatsky.core.script.Node.pre_transition`
    and :py:attr:`chatsky.core.script.Node.pre_response`.
    """
    return_type: ClassVar[Union[type, Tuple[type, ...]]] = NoneType

    @abstractmethod
    async def call(self, ctx: Context) -> None:
        raise NotImplementedError


class BasePriority(BaseScriptFunc, ABC):
    """
    Base class for priority functions.

    These are used in :py:attr:`chatsky.core.transition.Transition.priority`.

    Has several possible return types:

    - ``float``: Transition successful with the corresponding priority;
    - ``True`` or ``None``: Transition successful with the :py:attr:`~chatsky.core.pipeline.Pipeline.default_priority`;
    - ``False``: Transition unsuccessful.
    """
    return_type: ClassVar[Union[type, Tuple[type, ...]]] = (float, NoneType, bool)

    @abstractmethod
    async def call(self, ctx: Context) -> float | bool | None:
        raise NotImplementedError


class ConstPriority(ConstScriptFunc, BasePriority):
    root: Optional[float]


AnyPriority = Annotated[Union[ConstPriority, BasePriority], Field(union_mode="left_to_right")]
"""
A type annotation that allows accepting both :py:class:`ConstPriority` and :py:class:`BasePriority`
while validating :py:class:`ConstPriority` if possible.
"""
