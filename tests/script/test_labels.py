import pytest

from dff.script.labels import forward, repeat, previous, to_fallback, to_start, backward


class TestLabels:
    @pytest.fixture
    def ctx(self, context_factory):
        return context_factory(forbidden_fields=("requests", "responses", "misc"))

    def test_repeat(self, ctx, pipeline):
        assert repeat(5)(ctx, pipeline) == ("service", "start", 5)

        ctx.add_label(("flow", "node1"))
        assert repeat(4)(ctx, pipeline) == ("flow", "node1", 4)

        ctx.add_label(("flow", "node2"))
        assert repeat(3)(ctx, pipeline) == ("flow", "node2", 3)

    def test_previous(self, ctx, pipeline):
        assert previous(5)(ctx, pipeline) == ("service", "fallback", 5)

        ctx.add_label(("flow", "node1"))
        assert previous(4)(ctx, pipeline) == ("service", "start", 4)

        ctx.add_label(("flow", "node2"))
        assert previous(3)(ctx, pipeline) == ("flow", "node1", 3)

    def test_to_start(self, ctx, pipeline):
        assert to_start(5)(ctx, pipeline) == ("service", "start", 5)

    def test_to_fallback(self, ctx, pipeline):
        assert to_fallback(5)(ctx, pipeline) == ("service", "fallback", 5)

    def test_forward(self, ctx, pipeline):
        ctx.add_label(("flow", "node2"))
        assert forward(5)(ctx, pipeline) == ("flow", "node3", 5)

        ctx.add_label(("flow", "node3"))
        assert forward(4, cyclicality_flag=True)(ctx, pipeline) == ("flow", "node1", 4)
        assert forward(3, cyclicality_flag=False)(ctx, pipeline) == ("service", "fallback", 3)

    def test_backward(self, ctx, pipeline):
        ctx.add_label(("flow", "node2"))
        assert backward(5)(ctx, pipeline) == ("flow", "node1", 5)

        ctx.add_label(("flow", "node1"))
        assert backward(4, cyclicality_flag=True)(ctx, pipeline) == ("flow", "node3", 4)
        assert backward(3, cyclicality_flag=False)(ctx, pipeline) == ("service", "fallback", 3)
