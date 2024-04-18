import pytest
from pydantic import ValidationError

from dff.script import Message
import dff.script.conditions as cnd


class TestConditions:
    @pytest.fixture
    def _request_based_empty_ctx(self, context_factory):
        ctx = context_factory(forbidden_fields=("labels", "responses", "misc"))
        return ctx

    @pytest.fixture
    def request_based_ctx(self, _request_based_empty_ctx):
        _request_based_empty_ctx.add_request(Message("text", misc={"key": "value"}))
        return _request_based_empty_ctx

    def test_exact_match(self, request_based_ctx, pipeline):
        ctx = request_based_ctx

        assert cnd.exact_match(Message("text", misc={"key": "value"}))(ctx, pipeline) is True
        assert cnd.exact_match(Message("text"), skip_none=True)(ctx, pipeline) is True
        assert cnd.exact_match(Message("text"), skip_none=False)(ctx, pipeline) is False
        assert cnd.exact_match(Message(""))(ctx, pipeline) is False
        assert cnd.exact_match(Message("text", misc={"key": None}))(ctx, pipeline) is False
        assert cnd.exact_match(Message(), skip_none=True)(ctx, pipeline) is True
        assert cnd.exact_match(Message(), skip_none=False)(ctx, pipeline) is False

        class SubclassMessage(Message):
            additional_field: str

        assert (
            cnd.exact_match(SubclassMessage("text", misc={"key": "value"}, additional_field=""))(ctx, pipeline) is False
        )

    def test_has_text(self, request_based_ctx, pipeline):
        ctx = request_based_ctx

        assert cnd.has_text("text")(ctx, pipeline) is True
        assert cnd.has_text("te")(ctx, pipeline) is True
        assert cnd.has_text("text1")(ctx, pipeline) is False

    def test_regexp(self, request_based_ctx, pipeline, _request_based_empty_ctx):
        ctx = request_based_ctx

        assert cnd.regexp("t.*t")(ctx, pipeline) is True
        assert cnd.regexp("t.*t1")(ctx, pipeline) is False

        ctx = _request_based_empty_ctx
        ctx.add_request(Message())

        assert cnd.regexp("")(ctx, pipeline) is False

    def test_any(self, request_based_ctx, pipeline):
        ctx = request_based_ctx

        assert cnd.any([cnd.regexp("t.*"), cnd.regexp(".*t")])(ctx, pipeline) is True
        assert cnd.any([cnd.regexp("t.*"), cnd.regexp(".*t1")])(ctx, pipeline) is True
        assert cnd.any([cnd.regexp("1t.*"), cnd.regexp(".*t")])(ctx, pipeline) is True
        assert cnd.any([cnd.regexp("1t.*"), cnd.regexp(".*t1")])(ctx, pipeline) is False

        with pytest.raises(ValidationError):
            cnd.any([1])

    def test_all(self, request_based_ctx, pipeline):
        ctx = request_based_ctx

        assert cnd.all([cnd.regexp("t.*"), cnd.regexp(".*t")])(ctx, pipeline) is True
        assert cnd.all([cnd.regexp("t.*"), cnd.regexp(".*t1")])(ctx, pipeline) is False
        assert cnd.all([cnd.regexp("1t.*"), cnd.regexp(".*t")])(ctx, pipeline) is False
        assert cnd.all([cnd.regexp("1t.*"), cnd.regexp(".*t1")])(ctx, pipeline) is False

        with pytest.raises(ValidationError):
            cnd.all([1])

    def test_neg(self, request_based_ctx, pipeline):
        ctx = request_based_ctx

        assert cnd.neg(cnd.has_text("text"))(ctx, pipeline) is False
        assert cnd.neg(cnd.has_text("text1"))(ctx, pipeline) is True

    def test_has_last_labels(self, context_factory, pipeline):
        ctx = context_factory(forbidden_fields=("requests", "responses", "misc"))
        ctx.add_label(("flow", "node1"))

        assert cnd.has_last_labels(flow_labels=["flow"])(ctx, pipeline) is True
        assert cnd.has_last_labels(flow_labels=["flow1"])(ctx, pipeline) is False

        assert cnd.has_last_labels(labels=[("flow", "node1")])(ctx, pipeline) is True
        assert cnd.has_last_labels(labels=[("flow", "node2")])(ctx, pipeline) is False

        ctx.add_label(("service", "start"))

        assert cnd.has_last_labels(flow_labels=["flow"])(ctx, pipeline) is False
        assert cnd.has_last_labels(flow_labels=["flow"], last_n_indices=2)(ctx, pipeline) is True

        assert cnd.has_last_labels(labels=[("flow", "node1")])(ctx, pipeline) is False
        assert cnd.has_last_labels(labels=[("flow", "node1")], last_n_indices=2)(ctx, pipeline) is True

    def test_true_false(self, context_factory, pipeline):
        forbidden_context = context_factory(forbidden_fields=("requests", "responses", "labels", "misc"))

        assert cnd.true()(forbidden_context, pipeline) is True
        assert cnd.false()(forbidden_context, pipeline) is False
