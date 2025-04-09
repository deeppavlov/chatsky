import asyncio
import pytest
from chatsky import Context, GLOBAL, conditions, destinations as dst
from chatsky.core import Message, RESPONSE, TRANSITIONS, Pipeline, Transition as Tr, BaseCondition, BaseResponse

@pytest.mark.asyncio
async def test_update_ctx_misc():
    class MyCondition(BaseCondition):
        def call(self, ctx: Context) -> bool:
            return ctx.misc["condition"]

    toy_script = {
        "root": {
            "start": {TRANSITIONS: [Tr(dst="success", cnd=MyCondition())]},
            "success": {RESPONSE: "success", TRANSITIONS: [Tr(dst="success", cnd=MyCondition())]},
            "failure": {
                RESPONSE: "failure",
            },
        }
    }

    pipeline = Pipeline(script=toy_script, start_label=("root", "start"), fallback_label=("root", "failure"))

    ctx = await pipeline._run_pipeline(Message(), 0, update_ctx_misc={"condition": True})

    assert ctx.last_response.text == "success"

    ctx = await pipeline._run_pipeline(Message(), 0)

    assert ctx.last_response.text == "success"

    ctx = await pipeline._run_pipeline(Message(), 0, update_ctx_misc={"condition": False})

    assert ctx.last_response.text == "failure"


async def test_context_order():

    class LongResponse(BaseResponse):
        async def call(self, ctx: Context):
            await asyncio.sleep(int(ctx.last_request.text))
            return Message(text=ctx.last_request.text)

    toy_script = {
        "root": {
            "start": {RESPONSE: "", TRANSITIONS: [Tr(dst="result", cnd=True)]},
            "result": {RESPONSE: LongResponse(), TRANSITIONS: [Tr(dst="result", cnd=True)]},
            "failure": {RESPONSE: "failure"},
        },
    }

    pipeline = Pipeline(script=toy_script, start_label=("root", "start"), fallback_label=("root", "failure"))
    res = await asyncio.gather(
        pipeline._run_pipeline(Message("0.03"), ctx_id=0),
        pipeline._run_pipeline(Message("0.01"), ctx_id=1),
        pipeline._run_pipeline(Message("0.02"), ctx_id=0),
    )
    assert res[0].last_response == Message(text="0.01")
    assert res[1].last_response == Message(text="0.03")
    assert res[2].last_response == Message(text="0.02")
