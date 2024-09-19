import pytest

from chatsky.core import BaseCondition
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
    ctx.add_request(Message(text="text", misc={"key": "value"}))
    return ctx


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.ExactMatch(Message(text="text", misc={"key": "value"})), True),
        (cnd.ExactMatch(Message(text="text"), skip_none=True), True),
        (cnd.ExactMatch(Message(text="text"), skip_none=False), False),
        (cnd.ExactMatch("text", skip_none=True), True),
        (cnd.ExactMatch(Message(text="")), False),
        (cnd.ExactMatch(Message(text="text", misc={"key": None})), False),
        (cnd.ExactMatch(Message(), skip_none=True), True),
        (cnd.ExactMatch({}, skip_none=True), True),
        (cnd.ExactMatch(SubclassMessage(text="text", misc={"key": "value"}, additional_field="")), False),
    ],
)
async def test_exact_match(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.HasText("text"), True),
        (cnd.HasText("te"), True),
        (cnd.HasText("text1"), False),
    ],
)
async def test_has_text(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.Regexp("t.*t"), True),
        (cnd.Regexp("t.*t1"), False),
    ],
)
async def test_regexp(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.Any(cnd.Regexp("t.*"), cnd.Regexp(".*t")), True),
        (cnd.Any(FaultyCondition(), cnd.Regexp("t.*"), cnd.Regexp(".*t")), True),
        (cnd.Any(FaultyCondition()), False),
        (cnd.Any(cnd.Regexp("t.*"), cnd.Regexp(".*t1")), True),
        (cnd.Any(cnd.Regexp("1t.*"), cnd.Regexp(".*t1")), False),
    ],
)
async def test_any(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.All(cnd.Regexp("t.*"), cnd.Regexp(".*t")), True),
        (cnd.All(FaultyCondition(), cnd.Regexp("t.*"), cnd.Regexp(".*t")), False),
        (cnd.All(cnd.Regexp("t.*"), cnd.Regexp(".*t1")), False),
    ],
)
async def test_all(request_based_ctx, condition, result):
    assert await condition(request_based_ctx) is result


@pytest.mark.parametrize(
    "condition,result",
    [
        (cnd.Not(cnd.HasText("text")), False),
        (cnd.Not(cnd.HasText("text1")), True),
        (cnd.Not(FaultyCondition()), True),
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

    ctx.add_label(("service", "start"))

    assert await cnd.CheckLastLabels(flow_labels=["flow"])(ctx) is False
    assert await cnd.CheckLastLabels(flow_labels=["flow"], last_n_indices=2)(ctx) is True

    assert await cnd.CheckLastLabels(labels=[("flow", "node1")])(ctx) is False
    assert await cnd.CheckLastLabels(labels=[("flow", "node1")], last_n_indices=2)(ctx) is True


async def test_has_callback_query(context_factory):
    ctx = context_factory(forbidden_fields=("labels", "responses", "misc"))
    ctx.add_request(
        Message(attachments=[CallbackQuery(query_string="text", extra="extra"), CallbackQuery(query_string="text1")])
    )

    assert await cnd.HasCallbackQuery("text")(ctx) is True
    assert await cnd.HasCallbackQuery("t")(ctx) is False
    assert await cnd.HasCallbackQuery("text1")(ctx) is True


@pytest.mark.parametrize("cnd", [cnd.HasText(""), cnd.Regexp(""), cnd.HasCallbackQuery("")])
async def test_empty_text(context_factory, cnd):
    ctx = context_factory()
    ctx.add_request(Message())

    assert await cnd(ctx) is False
