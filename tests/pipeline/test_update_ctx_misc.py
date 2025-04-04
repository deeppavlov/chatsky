import asyncio
import pytest
import time
from chatsky import Context, GLOBAL, conditions
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


@pytest.mark.asyncio
async def test_context_order():

    class LongResponse(BaseResponse):
        def call(self, ctx: Context):
            time.sleep(3)
            return Message(text="Slept for 3 seconds")

    class LongerResponse(BaseResponse):
        def call(self, ctx: Context):
            time.sleep(5)
            return Message(text="Slept for 5 seconds")

    toy_script = {
        GLOBAL: {
            TRANSITIONS: [
                Tr(dst=("root", "5_sec"), cnd=conditions.ExactMatch("5"), priority=1.2),
                Tr(dst=("root", "3_sec"), cnd=conditions.ExactMatch("3"), priority=1.2),
            ]
        },
        "root": {
            "start": {TRANSITIONS: [Tr(dst="success", cnd=True)]},
            "5_sec": {RESPONSE: LongerResponse(), TRANSITIONS: [Tr(dst="start", cnd=True)]},
            "3_sec": {RESPONSE: LongResponse(), TRANSITIONS: [Tr(dst="start", cnd=True)]},
            "failure": {RESPONSE: "failure"},
        },
    }

    pipeline = Pipeline(script=toy_script, start_label=("root", "start"), fallback_label=("root", "failure"))
    res = await asyncio.gather(
        pipeline._run_pipeline(Message("5"), ctx_id=0),
        pipeline._run_pipeline(Message("3"), ctx_id=0),
    )
    assert res[0].last_response == Message(text="Slept for 5 seconds")
    assert res[1].last_response == Message(text="Slept for 3 seconds")
