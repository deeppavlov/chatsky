"""
Filters.
---------
This module contains a collection of basic functions for history filtering to avoid cluttering LLMs context window.
"""

from chatsky.script.core.message import Message
from chatsky.script import Context
from pydantic import BaseModel
import abc


class BaseFilter(BaseModel, abc.ABC):
    @abc.abstractmethod
    def __call__(self, ctx: Context, request: Message, response: Message, model_name: str) -> bool:
        raise NotImplementedError


class IsImportant(BaseFilter):
    def __call__(
        self, ctx: Context = None, request: Message = None, response: Message = None, model_name: str = None
    ) -> bool:
        if request and request.misc["important"]:
            return True
        if response and response.misc["important"]:
            return True
        return False


class FromTheModel(BaseFilter):
    def __call__(
        self, ctx: Context = None, request: Message = None, response: Message = None, model_name: str = None
    ) -> bool:
        if request is not None and request.annotation["__generated_by_model__"] == model_name:
            return True
        elif response is not None and response.annotation["__generated_by_model__"] == model_name:
            return True
        return False
