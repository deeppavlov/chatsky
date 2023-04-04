# %%
from dff.pipeline import Pipeline
from dff.script import Context, Message
import dff.script.conditions as cnd


def test_conditions():
    label = ("flow", "node")
    ctx = Context()
    ctx.add_request(Message(text="text", misc={}))
    ctx.add_label(label)
    failed_ctx = Context()
    failed_ctx.add_request(Message())
    failed_ctx.add_label(label)
    pipeline = Pipeline.from_script(script={"flow": {"node": {}}}, start_label=("flow", "node"))

    assert cnd.exact_match(Message(text="text"))(ctx, pipeline)
    assert cnd.exact_match(Message(text="text", misc={}))(ctx, pipeline)
    assert not cnd.exact_match(Message(text="text", misc={1: 1}))(ctx, pipeline)
    assert not cnd.exact_match(Message(text="text1"))(ctx, pipeline)
    assert cnd.exact_match(Message())(ctx, pipeline)
    assert not cnd.exact_match(Message(), skip_none=False)(ctx, pipeline)

    assert cnd.regexp("t.*t")(ctx, pipeline)
    assert not cnd.regexp("t.*t1")(ctx, pipeline)
    assert not cnd.regexp("t.*t1")(failed_ctx, pipeline)

    assert cnd.agg([cnd.regexp("t.*t"), cnd.exact_match(Message(text="text"))], aggregate_func=all)(ctx, pipeline)
    assert not cnd.agg([cnd.regexp("t.*t1"), cnd.exact_match(Message(text="text"))], aggregate_func=all)(ctx, pipeline)

    assert cnd.any([cnd.regexp("t.*t1"), cnd.exact_match(Message(text="text"))])(ctx, pipeline)
    assert not cnd.any([cnd.regexp("t.*t1"), cnd.exact_match(Message(text="text1"))])(ctx, pipeline)

    assert cnd.all([cnd.regexp("t.*t"), cnd.exact_match(Message(text="text"))])(ctx, pipeline)
    assert not cnd.all([cnd.regexp("t.*t1"), cnd.exact_match(Message(text="text"))])(ctx, pipeline)

    assert cnd.neg(cnd.exact_match(Message(text="text1")))(ctx, pipeline)
    assert not cnd.neg(cnd.exact_match(Message(text="text")))(ctx, pipeline)

    assert cnd.has_last_labels(flow_labels=["flow"])(ctx, pipeline)
    assert not cnd.has_last_labels(flow_labels=["flow1"])(ctx, pipeline)

    assert cnd.has_last_labels(labels=[("flow", "node")])(ctx, pipeline)
    assert not cnd.has_last_labels(labels=[("flow", "node1")])(ctx, pipeline)

    assert cnd.true()(ctx, pipeline)
    assert not cnd.false()(ctx, pipeline)

    try:
        cnd.any([123])
    except TypeError:
        pass

    def failed_cond_func(ctx: Context, pipeline: Pipeline, *args, **kwargs) -> bool:
        raise ValueError("Failed cnd")

    assert not cnd.any([failed_cond_func])(ctx, pipeline)
