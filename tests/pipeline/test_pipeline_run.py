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


async def test_context_lock():
    """Test execution blocking for same context ids."""
    logs = []

    class LongResponse(BaseResponse):
        async def call(self, ctx: Context):
            sleep_time = float(ctx.last_request.text)

            logs.append(f"pre_{sleep_time}")
            await asyncio.sleep(sleep_time)
            logs.append(f"post_{sleep_time}")
            return Message(text=str(sleep_time))

    toy_script = {
        "root": {
            "start": {RESPONSE: "", TRANSITIONS: [Tr(dst="result", cnd=True)]},
            "result": {RESPONSE: LongResponse(), TRANSITIONS: [Tr(dst="result", cnd=True)]},
            "failure": {RESPONSE: "failure"},
        },
    }

    pipeline = Pipeline(script=toy_script, start_label=("root", "start"), fallback_label=("root", "failure"))
    await asyncio.gather(
        pipeline._run_pipeline(Message("0.03"), ctx_id="0"),
        pipeline._run_pipeline(Message("0.01"), ctx_id="1"),
        pipeline._run_pipeline(Message("0.02"), ctx_id="0"),
    )
    assert logs == ["pre_0.03", "pre_0.01", "post_0.01", "post_0.03", "pre_0.02", "post_0.02"]
    assert list(pipeline._context_lock.keys()) == ["0", "1"]

    ctx = await pipeline._run_pipeline(Message("0.01"), ctx_id=None)

    assert list(pipeline._context_lock.keys()) == ["0", "1", ctx.id]
