import pytest
from pydantic import ValidationError

import chatsky.destinations.standard as dst
from chatsky.core.node_label import AbsoluteNodeLabel


@pytest.fixture
def ctx(context_factory):
    return context_factory(forbidden_fields=("requests", "responses", "misc"))


async def test_repeat(ctx):
    assert await dst.Repeat()(ctx) == AbsoluteNodeLabel(flow_name="service", node_name="start")
    with pytest.raises(KeyError):
        await dst.Repeat(shift=1)(ctx)

    ctx.add_label(("flow", "node1"))
    assert await dst.Repeat()(ctx) == AbsoluteNodeLabel(flow_name="flow", node_name="node1")
    assert await dst.Repeat(shift=1)(ctx) == AbsoluteNodeLabel(flow_name="service", node_name="start")
    with pytest.raises(KeyError):
        await dst.Repeat(shift=2)(ctx)

    ctx.add_label(("flow", "node2"))
    assert await dst.Repeat()(ctx) == AbsoluteNodeLabel(flow_name="flow", node_name="node2")


async def test_start(ctx):
    assert await dst.Start()(ctx) == AbsoluteNodeLabel(flow_name="service", node_name="start")


async def test_fallback(ctx):
    assert await dst.Fallback()(ctx) == AbsoluteNodeLabel(flow_name="service", node_name="fallback")


class TestForwardBackward:
    @pytest.mark.parametrize(
        "node,inc,loop,result",
        [
            (("flow", "node1"), True, False, ("flow", "node2")),
            (("flow", "node1"), False, True, ("flow", "node3")),
            (("flow", "node2"), True, False, ("flow", "node3")),
            (("flow", "node2"), False, False, ("flow", "node1")),
            (("flow", "node3"), True, True, ("flow", "node1")),
        ],
    )
    def test_get_next_node_in_flow(self, ctx, node, inc, loop, result):
        assert dst.get_next_node_in_flow(node, ctx, increment=inc, loop=loop) == AbsoluteNodeLabel.model_validate(
            result
        )

    @pytest.mark.parametrize(
        "node,inc,loop",
        [
            (("flow", "node1"), False, False),
            (("flow", "node3"), True, False),
        ],
    )
    def test_loop_exception(self, ctx, node, inc, loop):
        with pytest.raises(IndexError):
            dst.get_next_node_in_flow(node, ctx, increment=inc, loop=loop)

    def test_non_existent_node_exception(self, ctx):
        with pytest.raises(ValidationError):
            dst.get_next_node_in_flow(("flow", "node4"), ctx)

    async def test_forward(self, ctx):
        ctx.add_label(("flow", "node2"))
        assert await dst.Forward()(ctx) == AbsoluteNodeLabel(flow_name="flow", node_name="node3")

        ctx.add_label(("flow", "node3"))
        assert await dst.Forward(loop=True)(ctx) == AbsoluteNodeLabel(flow_name="flow", node_name="node1")
        with pytest.raises(IndexError):
            await dst.Forward(loop=False)(ctx)

    async def test_backward(self, ctx):
        ctx.add_label(("flow", "node2"))
        assert await dst.Backward()(ctx) == AbsoluteNodeLabel(flow_name="flow", node_name="node1")

        ctx.add_label(("flow", "node1"))
        assert await dst.Backward(loop=True)(ctx) == AbsoluteNodeLabel(flow_name="flow", node_name="node3")
        with pytest.raises(IndexError):
            await dst.Backward(loop=False)(ctx)
