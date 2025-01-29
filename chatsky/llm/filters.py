"""
Filters
---------
This module contains a collection of basic functions for history filtering to avoid cluttering LLMs context window.
"""

import abc
from enum import Enum
from logging import Logger
from typing import Union, Optional

from pydantic import BaseModel

from chatsky.core.message import Message
from chatsky.core.context import Context

logger = Logger(name=__name__)


class Return(Enum):
    Request = 1
    Response = 2
    Turn = 3


class BaseHistoryFilter(BaseModel, abc.ABC):
    """
    Base class for all message history filters.
    """

    @abc.abstractmethod
    def call(self, ctx: Context, request: Optional[Message], response: Optional[Message], llm_model_name: str) -> Union[Return, int]:
        """
        :param ctx: Context object.
        :param request: Request message.
        :param response: Response message.
        :param llm_model_name: Name of the model in the Pipeline.models.

        :return: Instance of Return enum or a corresponding int value.
        """
        raise NotImplementedError

    def __call__(self, ctx: Context, request: Message, response: Message, llm_model_name: str):
        """
        :param ctx: Context object.
        :param request: Request message.
        :param response: Response message.
        :param llm_model_name: Name of the model in the Pipeline.models.
        """
        try:
            result = self.call(ctx, request, response, llm_model_name)

            if isinstance(result, int):
                result = Return(result)
        except Exception as exc:
            logger.warning(exc)
            return []
        if result == Return.Turn:
            return [request, response]
        if result == Return.Response:
            return [response]
        if result == Return.Request:
            return [request]
        return []


class MessageFilter(BaseHistoryFilter):
    @abc.abstractmethod
    def call(self, ctx, message, llm_model_name) -> bool:
        raise NotImplementedError

    def __call__(self, ctx, request, response, llm_model_name):
        return (
            int(self.call(ctx, request, llm_model_name)) * Return.Request.value
            + int(self.call(ctx, response, llm_model_name)) * Return.Response.value
        )


class DefaultFilter(BaseHistoryFilter):
    def call(self, ctx: Context, request: Message, response: Message, llm_model_name: str) -> Union[Return, int]:
        return Return.Turn


class IsImportant(MessageFilter):
    """
    Filter that checks if the "important" field in a Message.misc is True.
    """

    def call(self, ctx: Context, message: Message, llm_model_name: str) -> bool:
        if message is not None and message.misc is not None and message.misc.get("important", None):
            return True
        return False


class FromModel(MessageFilter):
    """
    Filter that checks if the message was sent by the model.
    """

    def call(self, ctx: Context, message: Message, llm_model_name: str) -> bool:
        if (
            message is not None
            and message.annotations is not None
            and message.annotations.get("__generated_by_model__") == llm_model_name
        ):
            return True
        return False
