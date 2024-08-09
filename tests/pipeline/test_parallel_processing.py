import asyncio

import pytest

from chatsky.script import Message, GLOBAL, RESPONSE, PRE_RESPONSE_PROCESSING, TRANSITIONS, conditions as cnd
from chatsky.pipeline import Pipeline


@pytest.mark.asyncio
async def test_parallel_processing():
    async def fast_processing(ctx, _):
        processed_node = ctx.current_node
        await asyncio.sleep(1)
        processed_node.response = Message(f"fast: {processed_node.response.text}")

    async def slow_processing(ctx, _):
        processed_node = ctx.current_node
        await asyncio.sleep(2)
        processed_node.response = Message(f"slow: {processed_node.response.text}")

    toy_script = {
        GLOBAL: {
            PRE_RESPONSE_PROCESSING: {
                "first": slow_processing,
                "second": fast_processing,
            }
        },
        "root": {"start": {TRANSITIONS: {"main": cnd.true()}}, "main": {RESPONSE: Message("text")}},
    }

    # test sequential processing
    pipeline = Pipeline(script=toy_script, start_label=("root", "start"), parallelize_processing=False)

    ctx = await pipeline._run_pipeline(Message(), 0)

    assert ctx.last_response.text == "fast: slow: text"

    # test parallel processing
    pipeline = Pipeline(script=toy_script, start_label=("root", "start"), parallelize_processing=True)

    ctx = await pipeline._run_pipeline(Message(), 0)

    assert ctx.last_response.text == "slow: fast: text"
