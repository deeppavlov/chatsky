"""
Standard Processing
-------------------
This module provides basic processing functions.

- :py:class:`ModifyResponse` modifies response of the :py:attr:`.Context.current_node`.
"""

import abc
import logging
from typing import Literal, Type, Union, Dict
from pydantic import field_validator

from chatsky.core import BaseProcessing, BaseResponse, Context, MessageInitTypes, AnyResponse

logger = logging.getLogger(__name__)


class ModifyResponse(BaseProcessing, abc.ABC):
    """
    Modify the response function of the :py:attr:`.Context.current_node` to call
    :py:meth:`modified_response` instead.
    """

    @abc.abstractmethod
    async def modified_response(self, original_response: BaseResponse, ctx: Context) -> MessageInitTypes:
        """
        A function that replaces response of the current node.

        :param original_response: Response of the current node when :py:class:`.ModifyResponse` is called.
        :param ctx: Current context.

        :return: Message to replace original response with modified.
        """
        raise NotImplementedError

    async def call(self, ctx: Context) -> None:
        current_response = ctx.current_node.response
        if current_response is None:
            return

        processing_object = self

        class ModifiedResponse(BaseResponse):
            async def call(self, ctx: Context) -> MessageInitTypes:
                return await processing_object.modified_response(current_response, ctx)

        ctx.current_node.response = ModifiedResponse()


class AddFallbackResponses(ModifyResponse, arbitrary_types_allowed=True):
    """
    ModifyResponse with pre-response processing to handle exceptions dynamically.
    """

    exception_response: Dict[Union[Type[Exception], Literal["Else"]], AnyResponse]
    """
    Dictionary mapping exception types to fallback responses.
    """

    @field_validator("exception_response")
    @classmethod
    def validate_not_empty(cls, exception_response: dict) -> dict:
        """
        Validate that the `exception_response` dictionary is not empty.

        :param exception_response: Dictionary mapping exception types to fallback responses.
        :raises ValueError: If the `exception_response` dictionary is empty.
        :return: Not empty dictionary of exception_response.
        """
        if len(exception_response) == 0:
            raise ValueError("Exceptions dict is empty")
        return exception_response

    async def modified_response(self, original_response: BaseResponse, ctx: Context) -> MessageInitTypes:
        """
        Catch response errors and process them based on `exception_response`.

        :param original_response: The original response of the current node.
        :param ctx: The current context.

        :return: Message to replace original response with modified due to fallback response.
        """
        try:
            return await original_response(ctx)
        except Exception as e:
            exception = self.exception_response.get(type(e), self.exception_response.get("Else"))
            logger.exception(e)
            ctx.framework_data.response_exception = str(e)
            return await exception(ctx)
