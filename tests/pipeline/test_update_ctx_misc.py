import pytest

from chatsky.pipeline import Pipeline
from chatsky.script import Message, RESPONSE, TRANSITIONS


@pytest.mark.asyncio
async def test_update_ctx_misc():
    def condition(ctx, _):
        return ctx.misc["condition"]

    toy_script = {
        "root": {
            "start": {TRANSITIONS: {"success": condition}},
            "success": {RESPONSE: Message("success"), TRANSITIONS: {"success": condition}},
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
