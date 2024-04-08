import pytest

from dff.pipeline import Pipeline
from dff.script import Context
from dff.script.labels import forward, repeat, previous, to_fallback, to_start, backward


class TestLabels:
    pipeline = Pipeline.from_script(
        script={"flow": {"node1": {}, "node2": {}, "node3": {}}, "service": {"start": {}, "fallback": {}}},
        start_label=("service", "start"),
        fallback_label=("service", "fallback"),
    )

    @pytest.fixture
    def ctx(self):
        yield Context()

    def test_repeat(self, ctx):
        assert repeat(5)(ctx, self.pipeline) == ("service", "start", 5)

        ctx.add_label(("flow", "node1"))
        assert repeat(4)(ctx, self.pipeline) == ("flow", "node1", 4)

        ctx.add_label(("flow", "node2"))
        assert repeat(3)(ctx, self.pipeline) == ("flow", "node2", 3)

    def test_previous(self, ctx):
        assert previous(5)(ctx, self.pipeline) == ("service", "fallback", 5)

        ctx.add_label(("flow", "node1"))
        assert previous(4)(ctx, self.pipeline) == ("service", "start", 4)

        ctx.add_label(("flow", "node2"))
        assert previous(3)(ctx, self.pipeline) == ("flow", "node1", 3)

    def test_to_start(self, ctx):
        assert to_start(5)(ctx, self.pipeline) == ("service", "start", 5)

    def test_to_fallback(self, ctx):
        assert to_fallback(5)(ctx, self.pipeline) == ("service", "fallback", 5)

    def test_forward(self, ctx):
        ctx.add_label(("flow", "node2"))
        assert forward(5)(ctx, self.pipeline) == ("flow", "node3", 5)

        ctx.add_label(("flow", "node3"))
        assert forward(4, cyclicality_flag=True)(ctx, self.pipeline) == ("flow", "node1", 4)
        assert forward(3, cyclicality_flag=False)(ctx, self.pipeline) == ("service", "fallback", 3)

    def test_backward(self, ctx):
        ctx.add_label(("flow", "node2"))
        assert backward(5)(ctx, self.pipeline) == ("flow", "node1", 5)

        ctx.add_label(("flow", "node1"))
        assert backward(4, cyclicality_flag=True)(ctx, self.pipeline) == ("flow", "node3", 4)
        assert backward(3, cyclicality_flag=False)(ctx, self.pipeline) == ("service", "fallback", 3)
