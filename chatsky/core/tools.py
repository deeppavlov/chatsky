from __future__ import annotations
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, field_validator

T = TypeVar("T")


class ToolDict(BaseModel, Generic[T]):
    """
    TODO: Add docstrings
    """

    __pydantic_extra__: dict[str, T]
    default: Optional[str | T] = None

    @field_validator("default", mode="before")
    @classmethod
    def validate_default(cls, value: Optional[str | T]):
        if isinstance(value, str):
            if value == "default":
                raise ValueError("Default key cannot be 'default'.")
        return value

    def get(self, key: str) -> T:
        if key == "default":
            if self.default is None:
                raise ValueError('Default tool is not set. Add model under "default" key in the Pipeline tool dict.')
            if isinstance(self.default, str):
                return self.__pydantic_extra__.get(self.default)
            return self.default

        if key in self.__pydantic_extra__:
            return self.__pydantic_extra__[key]
        else:
            raise KeyError(f"Key '{key}' not found in ToolDict.")
