from chatsky import Context
from chatsky.core import Message, RESPONSE, TRANSITIONS, Pipeline, Transition as Tr

TOY_SCRIPT = {
    "test_flow": {
        "node1": {
            TRANSITIONS: [Tr(dst="node2")],
        },
        "node2": {
            RESPONSE: "Moved to node 2",
            TRANSITIONS: [Tr(dst="node3", passthrough=True)],
        },
        "node3": {
            RESPONSE: "Moved to node3",
            TRANSITIONS: [Tr(dst="node4", passthrough=True)],
        },
        "node4": {RESPONSE: "Moved to node4"},
        "fallback_node": {RESPONSE: "Ooops. Smth went wrong"},
    }
}


async def test_run_pipeline():
    pipeline = Pipeline(
        script=TOY_SCRIPT, start_label=("test_flow", "node1"), fallback_label=("test_flow", "fallback_node")
    )
    ctx = await pipeline.run_pipeline(Message(text="some text"), 0)
    assert len(ctx.responses) == 4
    requests = list(ctx.requests.values())
    assert requests[0] == Message(text="some text")
    assert requests[1:] == [Message()] * 3
