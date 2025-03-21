"""
Standard Processing
-------------------
This module provides basic processing functions.

- :py:class:`ModifyResponse` modifies response of the :py:attr:`.Context.current_node`.
"""

import abc
import logging

from chatsky.core import BaseProcessing, BaseResponse, Context, MessageInitTypes
from chatsky.messengers.common.interface import CallbackMessengerInterface


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


class ForwardRequest(BaseProcessing, abc.ABC):
    @abc.abstractmethod
    async def target_interface(self, ctx: Context) -> str:
        raise NotImplementedError
    
    @abc.abstractmethod
    async def target_context_id(self, ctx: Context) -> str:
        raise NotImplementedError

    async def call(self, ctx: Context) -> None:
        forward_id = self.target_interface(ctx)
        forward_iface = ctx.pipeline.messenger_interfaces.get(forward_id)
        if forward_iface is not None:
            if not isinstance(forward_iface, CallbackMessengerInterface):
                logger.error(f"Forwarding to the messenger interface '{forward_id}' of type {type(forward_iface).__name__} is impossible!")
            else:
                forward_request = ctx.last_response.model_copy()
                forward_request.misc["forwarded"] = ctx.id
                await forward_iface.on_request_async(forward_request, self.target_context_id(ctx))


class SaveRequestInfo(BaseProcessing):
    async def call(self, ctx: Context) -> None:
        last_request = ctx.last_request
        last_forwarded = last_request.misc.get("forward", None)
        if last_forwarded is not None:
            ctx.framework_data.last_forward_from = (ctx.last_request.origin.interface, last_forwarded)


class ForwardRequestUsingSavedInfo(ForwardRequest):
    async def target_interface(self, ctx: Context) -> str:
        return ctx.framework_data.last_forward_from[0]

    async def target_context_id(self, ctx: Context) -> str:
        return ctx.framework_data.last_forward_from[1]


class ForwardRequestUsingPredefinedInfo(ForwardRequest):
    constant_target_interface: str
    constant_target_context_id: str

    async def target_interface(self, _: Context) -> str:
        return self.constant_target_interface

    async def target_context_id(self, _: Context) -> str:
        return self.constant_target_context_id
