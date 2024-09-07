"""
Standard Processing
-------------------
This module provides basic processing functions.

- :py:class:`ModifyResponse` modifies response of the :py:attr:`.Context.current_node`.
"""

import abc

from chatsky.core import BaseProcessing, BaseResponse, Context, MessageInitTypes


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
