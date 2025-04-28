from __future__ import annotations
from typing import Generic, Optional, TypeVar
import logging

from pydantic import BaseModel

T = TypeVar("T")

logger = logging.getLogger(__name__)

class ToolDict(BaseModel, Generic[T]):
    __pydantic_extra__: dict[str, T]
    default: Optional[str | T] = None

    def get(self, key: str) -> T:
        if key in self.__pydantic_extra__:
            return self.__pydantic_extra__[key]
        else:
            logger.error(f"Key '{key}' not found in ToolDict.")
            raise KeyError(f"Key '{key}' not found in ToolDict.")