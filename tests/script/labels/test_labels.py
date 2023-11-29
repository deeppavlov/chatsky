from dff.pipeline import Pipeline
from dff.script import Context
from dff.script.labels import forward, repeat, previous, to_fallback, to_start, backward


def test_labels():
    ctx = Context()

    pipeline = Pipeline.from_script(
        script={"flow": {"node1": {}, "node2": {}, "node3": {}}, "service": {"start": {}, "fallback": {}}},
        start_label=("service", "start"),
        fallback_label=("service", "fallback"),
    )

    assert repeat(99)(ctx, pipeline) == ("service", "start", 99)
    assert previous(99)(ctx, pipeline) == ("service", "fallback", 99)

    ctx.add_label(["flow", "node1"])
    ctx.add_label(["flow", "node2"])
    ctx.add_label(["flow", "node3"])
    ctx.add_label(["flow", "node2"])

    assert repeat(99)(ctx, pipeline) == ("flow", "node2", 99)
    assert previous(99)(ctx, pipeline) == ("flow", "node3", 99)
    assert to_fallback(99)(ctx, pipeline) == ("service", "fallback", 99)
    assert to_start(99)(ctx, pipeline) == ("service", "start", 99)
    assert forward(99)(ctx, pipeline) == ("flow", "node3", 99)
    assert backward(99)(ctx, pipeline) == ("flow", "node1", 99)

    ctx.add_label(["flow", "node3"])
    assert forward(99)(ctx, pipeline) == ("flow", "node1", 99)
    assert forward(99, cyclicality_flag=False)(ctx, pipeline) == ("service", "fallback", 99)

    ctx.add_label(["flow", "node1"])
    assert backward(99)(ctx, pipeline) == ("flow", "node3", 99)
    assert backward(99, cyclicality_flag=False)(ctx, pipeline) == ("service", "fallback", 99)
    ctx = Context()
    ctx.add_label(["flow", "node2"])
    pipeline = Pipeline.from_script(
        script={"flow": {"node1": {}}, "service": {"start": {}, "fallback": {}}},
        start_label=("service", "start"),
        fallback_label=("service", "fallback"),
    )
    assert forward()(ctx, pipeline) == ("service", "fallback", 1.0)
