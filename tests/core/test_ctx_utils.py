from chatsky.core.context import Context
from chatsky.core.ctx_utils import Stages
from chatsky.core.script_function import BaseCondition, BaseResponse


class TestExceptionInfo:
    async def test_get_exception_info(self):
        class MyCondition1(BaseCondition):
            async def call(self, ctx):
                ctx.framework_data.current_stage = Stages.CONDITION
                raise RuntimeError("1")
                # add testcase for stage None --> add another error eg ValueError + recall MyCondition()

        ctx = Context()
        await MyCondition1().wrapped_call(ctx)
        result = ctx.framework_data.get_exception(stage=Stages.CONDITION)[1]
        assert result is not None
        assert result.__repr__() == "RuntimeError('1')"

        class MyCondition2(BaseCondition):
            async def call(self, ctx):
                ctx.framework_data.current_stage = Stages.CONDITION
                raise RuntimeError("2")

        class MyResponse1(BaseResponse):
            async def call(self, ctx):
                ctx.framework_data.current_stage = Stages.RESPONSE
                raise RuntimeError("3")

        class MyResponse2(BaseResponse):
            async def call(self, ctx):
                ctx.framework_data.current_stage = Stages.RESPONSE
                raise RuntimeError("4")

        await MyCondition2().wrapped_call(ctx)
        await MyResponse1().wrapped_call(ctx)
        await MyResponse2().wrapped_call(ctx)

        assert ctx.framework_data.get_exception(stage=Stages.CONDITION)[1].__repr__() == "RuntimeError('2')"
        assert ctx.framework_data.get_exception()[1].__repr__() == "RuntimeError('4')"
