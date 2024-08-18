from __future__ import annotations

from types import NoneType
from typing import Generic, TypeVar, Union, Tuple, ClassVar, Optional, Annotated
from abc import abstractmethod, ABC
import logging

from pydantic import BaseModel, model_validator, Field

from chatsky.utils.devel import wrap_sync_function_in_async
from chatsky.core.context import Context
from chatsky.core.message import Message, MessageInitTypes
from chatsky.core.node_label import NodeLabel, NodeLabelInitTypes, AbsoluteNodeLabel


logger = logging.getLogger(__name__)


ReturnType = TypeVar("ReturnType")


class BaseScriptFunc(BaseModel, ABC, Generic[ReturnType], frozen=True):
    return_type: ClassVar[Union[type, Tuple[type, ...]]]

    @abstractmethod
    async def func(self, ctx: Context):
        raise NotImplementedError()

    async def wrapped_call(self, ctx: Context, info: str = "") -> ReturnType | Exception:
        try:
            result = await wrap_sync_function_in_async(self.func, ctx)
            if not isinstance(self.return_type, tuple) and issubclass(self.return_type, BaseModel):
                result = self.return_type.model_validate(result, context={"ctx": ctx})
            if not isinstance(result, self.return_type):
                raise TypeError(
                    f"Function `func` of {self.__class__.__name__} should return {self.return_type!r}. "
                    f"Got instead: {result!r}"
                )
            logger.debug(f"Function {self.__class__.__name__} returned {result!r}. {info}")
            return result
        except Exception as exc:
            logger.warning(f"An exception occurred in {self.__class__.__name__}. {info}", exc_info=exc)
            return exc

    async def __call__(self, ctx: Context, info: str = "") -> ReturnType | Exception:
        return await self.wrapped_call(ctx, info)


class ConstScriptFunc(BaseScriptFunc, Generic[ReturnType]):
    root: ReturnType

    async def func(self, ctx: Context):
        return self.root

    @model_validator(mode="before")
    @classmethod
    def validate_value(cls, data):
        return {"root": data}


class BaseCondition(BaseScriptFunc[bool], ABC):
    return_type: ClassVar[Union[type, Tuple[type, ...]]] = bool

    @abstractmethod
    async def func(self, ctx: Context) -> bool:
        raise NotImplementedError

    async def __call__(self, ctx: Context, info: str = "") -> bool:
        result = await self.wrapped_call(ctx, info)
        if not isinstance(result, bool):
            return False
        return result


class ConstCondition(ConstScriptFunc[bool], BaseCondition):
    pass


AnyCondition = Annotated[Union[ConstCondition, BaseCondition], Field(union_mode="left_to_right")]


class BaseResponse(BaseScriptFunc[Message], ABC):
    return_type: ClassVar[Union[type, Tuple[type, ...]]] = Message

    @abstractmethod
    async def func(self, ctx: Context) -> MessageInitTypes:
        raise NotImplementedError


class ConstResponse(ConstScriptFunc[Message], BaseResponse):
    pass


AnyResponse = Annotated[Union[ConstResponse, BaseResponse], Field(union_mode="left_to_right")]


class BaseDestination(BaseScriptFunc[AbsoluteNodeLabel], ABC):
    return_type: ClassVar[Union[type, Tuple[type, ...]]] = AbsoluteNodeLabel

    @abstractmethod
    async def func(self, ctx: Context) -> NodeLabelInitTypes:
        raise NotImplementedError


class ConstDestination(ConstScriptFunc[NodeLabel], BaseDestination):
    pass


AnyDestination = Annotated[Union[ConstDestination, BaseDestination], Field(union_mode="left_to_right")]


class BaseProcessing(BaseScriptFunc[None], ABC):
    return_type: ClassVar[Union[type, Tuple[type, ...]]] = NoneType

    @abstractmethod
    async def func(self, ctx: Context) -> None:
        raise NotImplementedError


class BasePriority(BaseScriptFunc[Union[float, None, bool]], ABC):
    return_type: ClassVar[Union[type, Tuple[type, ...]]] = (float, NoneType, bool)

    @abstractmethod
    async def func(self, ctx: Context) -> float | bool | None:
        raise NotImplementedError


class ConstPriority(ConstScriptFunc[Optional[float]], BasePriority):
    pass


AnyPriority = Annotated[Union[ConstPriority, BasePriority], Field(union_mode="left_to_right")]
