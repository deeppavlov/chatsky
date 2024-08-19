import pytest

from chatsky import Context
from chatsky.core import Message, RESPONSE, TRANSITIONS, Pipeline, Transition as Tr, BaseCondition


@pytest.mark.asyncio
async def test_update_ctx_misc():
    class MyCondition(BaseCondition):
        async def func(self, ctx: Context) -> bool:
            return ctx.misc["condition"]

    toy_script = {
        "root": {
            "start": {TRANSITIONS: [Tr(dst="success", cnd=MyCondition())]},
            "success": {RESPONSE: Message("success"), TRANSITIONS: [Tr(dst="success", cnd=MyCondition())]},
            "failure": {
                RESPONSE: Message("failure"),
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
