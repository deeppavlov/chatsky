import pytest

from chatsky.core import BaseCondition, AbsoluteNodeLabel
from chatsky.core.message import Message, CallbackQuery
import chatsky.conditions as cnd


class FaultyCondition(BaseCondition):
    async def call(self, ctx) -> bool:
        raise RuntimeError()


class SubclassMessage(Message):
    additional_field: str


@pytest.fixture
def request_based_ctx(context_factory):
    ctx = context_factory(forbidden_fields=("labels", "responses", "misc"))
    ctx.requests[1] = Message(text="text", misc={"key": "value"})
    return ctx


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.ExactMatch(match=Message(text="text", misc={"key": "value"})), True),
        (cnd.ExactMatch(match=Message(text="text"), skip_none=True), True),
        (cnd.ExactMatch(match=Message(text="text"), skip_none=False), False),
        (cnd.ExactMatch(match="text", skip_none=True), True),
        (cnd.ExactMatch(match=Message(text="")), False),
        (cnd.ExactMatch(match=Message(text="text", misc={"key": None})), False),
        (cnd.ExactMatch(match=Message(), skip_none=True), True),
        (cnd.ExactMatch(match={}, skip_none=True), True),
        (cnd.ExactMatch(match=SubclassMessage(text="text", misc={"key": "value"}, additional_field="")), False),
    ],
)
async def test_exact_match(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.HasText(text="text"), True),
        (cnd.HasText(text="te"), True),
        (cnd.HasText(text="text1"), False),
    ],
)
async def test_has_text(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.Regexp(pattern="t.*t"), True),
        (cnd.Regexp(pattern="t.*t1"), False),
    ],
)
async def test_regexp(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.Any(conditions=[cnd.Regexp(pattern="t.*"), cnd.Regexp(pattern=".*t")]), True),
        (cnd.Any(conditions=[FaultyCondition(), cnd.Regexp(pattern="t.*"), cnd.Regexp(pattern=".*t")]), True),
        (cnd.Any(conditions=[FaultyCondition()]), False),
        (cnd.Any(conditions=[cnd.Regexp(pattern="t.*"), cnd.Regexp(pattern=".*t1")]), True),
        (cnd.Any(conditions=[cnd.Regexp(pattern="1t.*"), cnd.Regexp(pattern=".*t1")]), False),
    ],
)
async def test_any(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.All(conditions=[cnd.Regexp(pattern="t.*"), cnd.Regexp(pattern=".*t")]), True),
        (cnd.All(conditions=[FaultyCondition(), cnd.Regexp(pattern="t.*"), cnd.Regexp(pattern=".*t")]), False),
        (cnd.All(conditions=[cnd.Regexp(pattern="t.*"), cnd.Regexp(pattern=".*t1")]), False),
    ],
)
async def test_all(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.Not(condition=cnd.HasText(text="text")), False),
        (cnd.Not(condition=cnd.HasText(text="text1")), True),
        (cnd.Not(condition=FaultyCondition()), True),
    ],
)
async def test_neg(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


async def test_has_last_labels(context_factory):
    ctx = context_factory(forbidden_fields=("requests", "responses", "misc"), start_label=("flow", "node1"))

    assert await cnd.CheckLastLabels(flow_labels=["flow"])(ctx) is True
    assert await cnd.CheckLastLabels(flow_labels=["flow1"])(ctx) is False

    assert await cnd.CheckLastLabels(labels=[("flow", "node1")])(ctx) is True
    assert await cnd.CheckLastLabels(labels=[("flow", "node2")])(ctx) is False

    ctx.labels[1] = AbsoluteNodeLabel(flow_name="service", node_name="start")

    assert await cnd.CheckLastLabels(flow_labels=["flow"])(ctx) is False
    assert await cnd.CheckLastLabels(flow_labels=["flow"], last_n_indices=2)(ctx) is True

    assert await cnd.CheckLastLabels(labels=[("flow", "node1")])(ctx) is False
    assert await cnd.CheckLastLabels(labels=[("flow", "node1")], last_n_indices=2)(ctx) is True


async def test_has_callback_query(context_factory):
    ctx = context_factory(forbidden_fields=("labels", "responses", "misc"))
    ctx.requests[1] = Message(
        attachments=[CallbackQuery(query_string="text", extra="extra"), CallbackQuery(query_string="text1")]
    )

    assert await cnd.HasCallbackQuery("text")(ctx) is True
    assert await cnd.HasCallbackQuery("t")(ctx) is False
    assert await cnd.HasCallbackQuery("text1")(ctx) is True


@pytest.mark.parametrize("cnd", [cnd.HasText(text=""), cnd.Regexp(pattern=""), cnd.HasCallbackQuery("")])
async def test_empty_text(context_factory, cnd):
    ctx = context_factory()
    ctx.requests[1] = Message()

    assert await cnd(ctx) is False
