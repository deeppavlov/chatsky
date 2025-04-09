import asyncio

from chatsky import Context
from chatsky.core import Message, RESPONSE, TRANSITIONS, Pipeline, Transition as Tr, BaseCondition, BaseResponse


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

    logs = []

    class LongResponse(BaseResponse):
        async def call(self, ctx: Context):
            await asyncio.sleep(float(ctx.last_request.text))
            logs.append(Message(text=ctx.last_request.text))
            return Message(text=ctx.last_request.text)

    toy_script = {
        "root": {
            "start": {RESPONSE: "", TRANSITIONS: [Tr(dst="result", cnd=True)]},
            "result": {RESPONSE: LongResponse(), TRANSITIONS: [Tr(dst="result", cnd=True)]},
            "failure": {RESPONSE: "failure"},
        },
    }

    pipeline = Pipeline(script=toy_script, start_label=("root", "start"), fallback_label=("root", "failure"))
    await asyncio.gather(
        pipeline._run_pipeline(Message("0.03"), ctx_id=0),
        pipeline._run_pipeline(Message("0.01"), ctx_id=1),
        pipeline._run_pipeline(Message("0.02"), ctx_id=0),
    )
    assert logs[0] == Message(text="0.01")
    assert logs[1] == Message(text="0.03")
    assert logs[2] == Message(text="0.02")
