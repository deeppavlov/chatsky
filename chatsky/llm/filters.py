"""
Filters
---------
This module contains a collection of basic functions for history filtering to avoid cluttering LLMs context window.
"""

import abc
from enum import Enum
from pydantic import BaseModel

from logging import Logger

from chatsky.core.message import Message
from chatsky.core.context import Context

logger = Logger(name=__name__)


class BaseHistoryFilter(BaseModel, abc.ABC):
    """
    Base class for all message history filters.
    """

    class Return(Enum):
        Request = 1
        Response = 2
        Turn = 3

    def call(self, ctx: Context, request: Message, response: Message, model_name: str):
        return self.Return.Turn

    def __call__(self, ctx: Context, request: Message, response: Message, model_name: str) -> bool:
        """
        :param ctx: Context object.
        :param request: Request message.
        :param response: Response message.
        :param model_name: Name of the model in the Pipeline.models.
        """
        try:
            result = self.call(ctx, request, response, model_name)
        except Exception as exc:
            logger.warning(exc)
            return []
        if result == self.Return.Turn:
            return [request, response]
        if result == self.Return.Response:
            return [response]
        if result == self.Return.Request:
            return [request]
        return []


class MessageFilter(BaseHistoryFilter):
    @abc.abstractmethod
    def call(self, ctx, message, model_name):
        raise NotImplementedError

    def __call__(self, ctx, request, response, model_name):
        return self.call(ctx, request, model_name) + self.call(ctx, response, model_name)


class IsImportant(BaseHistoryFilter):
    """
    Filter that checks if the "important" field in a Message.misc is True.
    """

    def call(self, ctx: Context, request: Message, response: Message, model_name: str) -> bool:
        if request is not None and request.misc is not None and request.misc.get("important", None):
            return self.Return.Request
        if response is not None and response.misc is not None and response.misc.get("important", None):
            return self.Return.Response
        return False


class FromModel(BaseHistoryFilter):
    """
    Filter that checks if the message was sent by the model.
    """

    def call(self, ctx: Context, request: Message, response: Message, model_name: str) -> bool:
        if (
            request is not None
            and request.annotations is not None
            and request.annotations.get("__generated_by_model__") == model_name
        ):
            return self.Return.Request
        elif (
            response is not None
            and response.annotations is not None
            and response.annotations.get("__generated_by_model__") == model_name
        ):
            return self.Return.Response
        return False
