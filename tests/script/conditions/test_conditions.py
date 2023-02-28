# %%
from dff.script import Context, Actor, Message
import dff.script.conditions as cnd


def test_conditions():
    label = ("flow", "node")
    ctx = Context()
    ctx.add_request(Message(text="text", misc={}))
    ctx.add_label(label)
    failed_ctx = Context()
    failed_ctx.add_request(Message())
    failed_ctx.add_label(label)
    actor = Actor(script={"flow": {"node": {}}}, start_label=("flow", "node"))

    assert cnd.exact_match(Message(text="text"))(ctx, actor)
    assert cnd.exact_match(Message(text="text", misc={}))(ctx, actor)
    assert not cnd.exact_match(Message(text="text", misc={1: 1}))(ctx, actor)
    assert not cnd.exact_match(Message(text="text1"))(ctx, actor)
    assert cnd.exact_match(Message())(ctx, actor)
    assert not cnd.exact_match(Message(), skip_none=False)(ctx, actor)

    assert cnd.regexp("t.*t")(ctx, actor)
    assert not cnd.regexp("t.*t1")(ctx, actor)
    assert not cnd.regexp("t.*t1")(failed_ctx, actor)

    assert cnd.agg([cnd.regexp("t.*t"), cnd.exact_match(Message(text="text"))], aggregate_func=all)(ctx, actor)
    assert not cnd.agg([cnd.regexp("t.*t1"), cnd.exact_match(Message(text="text"))], aggregate_func=all)(ctx, actor)

    assert cnd.any([cnd.regexp("t.*t1"), cnd.exact_match(Message(text="text"))])(ctx, actor)
    assert not cnd.any([cnd.regexp("t.*t1"), cnd.exact_match(Message(text="text1"))])(ctx, actor)

    assert cnd.all([cnd.regexp("t.*t"), cnd.exact_match(Message(text="text"))])(ctx, actor)
    assert not cnd.all([cnd.regexp("t.*t1"), cnd.exact_match(Message(text="text"))])(ctx, actor)

    assert cnd.neg(cnd.exact_match(Message(text="text1")))(ctx, actor)
    assert not cnd.neg(cnd.exact_match(Message(text="text")))(ctx, actor)

    assert cnd.has_last_labels(flow_labels=["flow"])(ctx, actor)
    assert not cnd.has_last_labels(flow_labels=["flow1"])(ctx, actor)

    assert cnd.has_last_labels(labels=[("flow", "node")])(ctx, actor)
    assert not cnd.has_last_labels(labels=[("flow", "node1")])(ctx, actor)

    assert cnd.true()(ctx, actor)
    assert not cnd.false()(ctx, actor)

    try:
        cnd.any([123])
    except TypeError:
        pass

    def failed_cond_func(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        raise ValueError("Failed cnd")

    assert not cnd.any([failed_cond_func])(ctx, actor)
