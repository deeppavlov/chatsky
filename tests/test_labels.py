from df_engine.core import Context, Actor
from df_engine.labels import forward, repeat, previous, to_fallback, to_start, backward


def test_labels():
    ctx = Context()
    ctx.add_label(["flow", "node1"])
    ctx.add_label(["flow", "node2"])
    ctx.add_label(["flow", "node3"])
    ctx.add_label(["flow", "node2"])
    actor = Actor(
        script={"flow": {"node1": {}, "node2": {}, "node3": {}}, "service": {"start": {}, "fallback": {}}},
        start_label=("service", "start"),
        fallback_label=("service", "fallback"),
    )

    assert repeat(99)(ctx, actor) == ("flow", "node2", 99)
    assert previous(99)(ctx, actor) == ("flow", "node3", 99)
    assert to_fallback(99)(ctx, actor) == ("service", "fallback", 99)
    assert to_start(99)(ctx, actor) == ("service", "start", 99)
    assert forward(99)(ctx, actor) == ("flow", "node3", 99)
    assert backward(99)(ctx, actor) == ("flow", "node1", 99)

    ctx.add_label(["flow", "node3"])
    assert forward(99)(ctx, actor) == ("flow", "node1", 99)
    assert forward(99, cyclicality_flag=False)(ctx, actor) == ("service", "fallback", 99)

    ctx.add_label(["flow", "node1"])
    assert backward(99)(ctx, actor) == ("flow", "node3", 99)
    assert backward(99, cyclicality_flag=False)(ctx, actor) == ("service", "fallback", 99)
    ctx = Context()
    ctx.add_label(["flow", "node2"])
    actor = Actor(
        script={"flow": {"node1": {}}, "service": {"start": {}, "fallback": {}}},
        start_label=("service", "start"),
        fallback_label=("service", "fallback"),
    )
    assert forward()(ctx, actor) == ("service", "fallback", 1.0)
