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
    """
    Base class for all message history filters.
    """
    @abc.abstractmethod
    def __call__(self, ctx: Context, request: Message, response: Message, model_name: str) -> bool:
        """
        :param Context ctx: Context object.
        :param Message request: Request message.
        :param Message response: Response message.
        :param str model_name: Name of the model in the Pipeline.models.
        """
        raise NotImplementedError


class IsImportant(BaseFilter):
    """
    Filter that checks if the "important" field in a Message.misc is True.
    """
    def __call__(
        self, ctx: Context = None, request: Message = None, response: Message = None, model_name: str = None
    ) -> bool:
        if request and request.misc["important"]:
            return True
        if response and response.misc["important"]:
            return True
        return False


class FromTheModel(BaseFilter):
    """
    Filter that checks if the message was sent by the model.
    """
    def __call__(
        self, ctx: Context = None, request: Message = None, response: Message = None, model_name: str = None
    ) -> bool:
        if request is not None and request.annotation["__generated_by_model__"] == model_name:
            return True
        elif response is not None and response.annotation["__generated_by_model__"] == model_name:
            return True
        return False
