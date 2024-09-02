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
