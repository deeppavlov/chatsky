"""
Standard Processing
-------------------
This module provides basic processing functions.

- :py:class:`ModifyResponse` modifies response of the :py:attr:`.Context.current_node`.
"""

import abc
from typing import Literal, Type, Union, Dict
from pydantic import field_validator

from chatsky.core import BaseProcessing, BaseResponse, Context, MessageInitTypes, AnyResponse


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


class FallbackResponse(ModifyResponse, arbitrary_types_allowed=True):
    """
    ModifyResponse with pre-response processing to handle exceptions dynamically.
    """

    exceptions: Dict[Union[Type[Exception], Literal["Else"]], AnyResponse]
    """
    Dictionary mapping exception types to fallback responses.
    """

    @field_validator("exceptions")
    @classmethod
    def validate_not_empty(cls, exceptions: dict) -> dict:
        """
        Validate that the `exceptions` dictionary is not empty.

        :param exceptions: Dictionary mapping exception types to fallback responses.
        :raises ValueError: If the `exceptions` dictionary is empty.
        :return: Not empty dictionary of exceptions.
        """
        if len(exceptions) == 0:
            raise ValueError("Exceptions dict is empty")
        return exceptions

    async def modified_response(self, original_response: BaseResponse, ctx: Context) -> MessageInitTypes:
        """
        Catch response errors and process them based on `exceptions`.

        :param original_response: The original response of the current node.
        :param ctx: The current context.

        :return: Message to replace original response with modified due to fallback response.
        """
        print("fallback modified framework", ctx.framework_data)
        try:
            return await original_response(ctx)
        except Exception as e:
            exception = self.exceptions.get(type(e), self.exceptions.get("Else"))
            print(e, type(e), str(e))
            ctx.framework_data.response_exception = str(e)
            return await exception(ctx)
