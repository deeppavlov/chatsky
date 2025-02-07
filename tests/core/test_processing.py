import pytest

from chatsky import proc, Context, BaseResponse, MessageInitTypes, Message
from chatsky.core.script import Node


async def test_modify_response():
    ctx = Context()
    ctx.framework_data.current_node = Node()

    class MyModifiedResponse(proc.ModifyResponse):
        async def modified_response(self, original_response: BaseResponse, ctx: Context) -> MessageInitTypes:
            result = await original_response(ctx)
            return Message(misc={"msg": result})

    await MyModifiedResponse()(ctx)

    assert ctx.current_node.response is None

    ctx.framework_data.current_node = Node(response="hi")

    await MyModifiedResponse()(ctx)

    assert ctx.current_node.response.__class__.__name__ == "ModifiedResponse"

    assert await ctx.current_node.response(ctx) == Message(misc={"msg": Message("hi")})


class TestAddFallbackResponses:
    """
    A class to group and test the functionality of FallbackResponse.
    """

    class ReturnException(BaseResponse):
        async def call(self, ctx: Context):
            return ctx.framework_data.response_exception

    class RaiseException(BaseResponse, arbitrary_types_allowed=True):
        exception: Exception

        async def call(self, ctx: Context):
            raise self.exception

    @pytest.mark.parametrize(
        "response_with_exception, expected_response",
        [
            (RaiseException(exception=OverflowError()), "Overflow!"),
            (RaiseException(exception=KeyError()), "Other exception occured"),
            (RaiseException(exception=ValueError("some text")), "some text"),
        ],
    )
    @pytest.mark.asyncio
    async def test_fallback_response(self, response_with_exception, expected_response):
        ctx = Context()
        ctx.framework_data.current_node = Node()

        exceptions = {OverflowError: "Overflow!", ValueError: self.ReturnException(), "Else": "Other exception occured"}

        fallback_response = proc.AddFallbackResponses(exception_response=exceptions)
        ctx.current_node.response = response_with_exception
        await fallback_response(ctx)
        assert await ctx.current_node.response(ctx) == Message(text=expected_response)

    async def test_fallback_empty_exceptions(self):
        ctx = Context()
        ctx.framework_data.current_node = Node()

        exceptions = {}
        with pytest.raises(ValueError, match="Exceptions dict is empty"):
            proc.AddFallbackResponses(exception_response=exceptions)
