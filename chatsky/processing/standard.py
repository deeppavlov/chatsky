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

        :return: Message to replace original response with.
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


class AddFallbackResponses(ModifyResponse):
    """
    ModifyResponse with dynamical pre-response processing to handle
    exceptions from user-provided exceptions dictionary
    and keeping them in :py:attr:`ctx.framework_data.response_exception`.

    Example:
    .. code-block:: python

        class ReturnException(BaseResponse):
            async def call(self, ctx: Context):
                return ctx.framework_data.response_exception

        # Define user-provided exceptions dictionary
        exceptions = {
            "OverflowError": "Overflow!",
            "ValueError": self.ReturnException(),
            "Else": "Other exception occured",
        }

        # AddFallbackResponses class initialization
        fallback_response = AddFallbackResponses(exception_responses=exceptions)

        # Apply fallback response pre-processing
        await fallback_response(ctx)

        # Get final response
        await ctx.current_node.response(ctx)
    """

    exception_responses: Dict[Union[str, Literal["Else"]], AnyResponse]
    """
    Dictionary mapping exception types to fallback responses.
    """

    @field_validator("exception_responses")
    @classmethod
    def validate_not_empty(cls, exception_responses: dict) -> dict:
        """
        Validate that the `exception_responses` dictionary is not empty.

        :param exception_responses: Dictionary mapping exception types to fallback responses.
        :raises ValueError: If the `exception_responses` dictionary is empty.
        :return: Not empty dictionary of exception_responses.
        """
        if len(exception_responses) == 0:
            raise ValueError("Exceptions dict is empty")
        return exception_responses

    async def modified_response(self, original_response: BaseResponse, ctx: Context) -> MessageInitTypes:
        """
        Catch response errors and process them based on `exception_responses` dictionary.

        :param original_response: The original response of the current node.
        :param ctx: The current context.

        :return: Message to replace original response with.
        """
        result = await original_response.wrapped_call(ctx)
        if isinstance(result, Exception):
            exception_response = self.exception_responses.get(
                type(result).__name__, self.exception_responses.get("Else")
            )
            ctx.framework_data.response_exception = repr(result)
            if exception_response is None:
                raise result
            return await exception_response(ctx)
        else:
            return result
