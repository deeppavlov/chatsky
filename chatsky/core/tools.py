from __future__ import annotations
from pydantic import BaseModel
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class ToolDict(BaseModel, Generic[T]):
    __pydantic_extra__: dict[str, T]
    default: Optional[str | T] = None
