"""
Filters
---------
This module contains a collection of basic functions for history filtering to avoid cluttering LLMs context window.
"""

import abc

from pydantic import BaseModel

from chatsky.core.message import Message
from chatsky.core.context import Context


class BaseFilter(BaseModel, abc.ABC):
    """
    Base class for all message history filters.
    """

    @abc.abstractmethod
    def __call__(self, ctx: Context, request: Message, response: Message, model_name: str) -> bool:
        """
        :param ctx: Context object.
        :param request: Request message.
        :param response: Response message.
        :param model_name: Name of the model in the Pipeline.models.
        """
        return True


class IsImportant(BaseFilter):
    """
    Filter that checks if the "important" field in a Message.misc is True.
    """

    def __call__(self, ctx: Context, request: Message, response: Message, model_name: str) -> bool:
        if request is not None and request.misc is not None and request.misc.get("important", None):
            return True
        if response is not None and response.misc is not None and response.misc.get("important", None):
            return True
        return False


class FromTheModel(BaseFilter):
    """
    Filter that checks if the message was sent by the model.
    """

    def __call__(self, ctx: Context, request: Message, response: Message, model_name: str) -> bool:
        if (
            request is not None
            and request.annotations is not None
            and request.annotations.get("__generated_by_model__") == model_name
        ):
            return True
        elif (
            response is not None
            and response.annotations is not None
            and response.annotations.get("__generated_by_model__") == model_name
        ):
            return True
        return False
