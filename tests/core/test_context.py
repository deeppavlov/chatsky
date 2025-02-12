from copy import copy
import pytest

from chatsky.core.context import Context, ContextError
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.message import Message, MessageInitTypes
from chatsky.core.script_function import BaseResponse, BaseProcessing
from chatsky.core.pipeline import Pipeline
from chatsky.core import RESPONSE, PRE_TRANSITION, PRE_RESPONSE


class TestLabels:
    @pytest.fixture
    def ctx(self, context_factory):
        return context_factory(forbidden_fields=["requests", "responses"])

    def test_raises_on_empty_labels(self, ctx: Context):
        with pytest.raises(ContextError):
            ctx.last_label

    def test_existing_labels(self, ctx: Context):
        ctx.labels[5] = ("flow", "node1")

        assert ctx.last_label == AbsoluteNodeLabel(flow_name="flow", node_name="node1")
        ctx.labels[6] = ("flow", "node2")
        assert ctx.labels.keys() == [5, 6]
        assert ctx.last_label == AbsoluteNodeLabel(flow_name="flow", node_name="node2")


class TestRequests:
    @pytest.fixture
    def ctx(self, context_factory):
        return context_factory(forbidden_fields=["labels", "responses"])

    def test_existing_requests(self, ctx: Context):
        ctx.requests[5] = Message(text="text1")
        assert ctx.last_request == Message(text="text1")
        ctx.requests[6] = "text2"
        assert ctx.requests.keys() == [5, 6]
        assert ctx.last_request == Message(text="text2")

    def test_empty_requests(self, ctx: Context):
        with pytest.raises(ContextError):
            ctx.last_request

        ctx.requests[1] = "text"
        assert ctx.last_request == Message(text="text")
        assert ctx.requests.keys() == [1]


class TestResponses:
    @pytest.fixture
    def ctx(self, context_factory):
        return context_factory(forbidden_fields=["labels", "requests"])

    def test_existing_responses(self, ctx: Context):
        ctx.responses[5] = Message(text="text1")
        assert ctx.last_response == Message(text="text1")
        ctx.responses[6] = "text2"
        assert ctx.responses.keys() == [5, 6]
        assert ctx.last_response == Message(text="text2")

    def test_empty_responses(self, ctx: Context):
        with pytest.raises(ContextError):
            ctx.last_response

        ctx.responses[1] = "text"
        assert ctx.last_response == Message(text="text")
        assert ctx.responses.keys() == [1]


class TestTurns:
    @pytest.fixture
    def ctx(self, context_factory):
        return context_factory()

    async def test_complete_turn(self, ctx: Context):
        ctx.labels[5] = ("flow", "node5")
        ctx.requests[5] = Message(text="text5")
        ctx.responses[5] = Message(text="text5")
        ctx.current_turn_id = 5

        label, request, response = list(await ctx.turns(5))[0]
        assert label == AbsoluteNodeLabel(flow_name="flow", node_name="node5")
        assert request == Message(text="text5")
        assert response == Message(text="text5")

    async def test_partial_turn(self, ctx: Context):
        ctx.labels[6] = ("flow", "node6")
        ctx.requests[6] = Message(text="text6")
        ctx.current_turn_id = 6

        label, request, response = list(await ctx.turns(6))[0]
        assert label == AbsoluteNodeLabel(flow_name="flow", node_name="node6")
        assert request == Message(text="text6")
        assert response is None

    async def test_slice_turn(self, ctx: Context):
        for i in range(2, 6):
            ctx.labels[i] = ("flow", f"node{i}")
            ctx.requests[i] = Message(text=f"text{i}")
            ctx.responses[i] = Message(text=f"text{i}")
            ctx.current_turn_id = i

        labels, requests, responses = zip(*(await ctx.turns(slice(2, 6))))
        for i in range(2, 6):
            assert AbsoluteNodeLabel(flow_name="flow", node_name=f"node{i}") in labels
            assert Message(text=f"text{i}") in requests
            assert Message(text=f"text{i}") in responses


async def test_copy(context_factory):
    ctx = context_factory()
    ctx.misc["key"] = "value"

    cpy = copy(ctx)
    assert cpy.misc["key"] == "value"
    assert cpy._storage == ctx._storage
    assert cpy == ctx


async def test_pipeline_available():
    class MyResponse(BaseResponse):
        async def call(self, ctx: Context) -> MessageInitTypes:
            return ctx.pipeline.start_label.node_name

    pipeline = Pipeline(script={"flow": {"node": {RESPONSE: MyResponse()}}}, start_label=("flow", "node"))
    ctx = await pipeline._run_pipeline(Message(text=""))

    assert ctx.last_response == Message(text="node")

    ctx.framework_data.pipeline = None
    with pytest.raises(ContextError):
        await MyResponse().call(ctx)


async def test_current_node_available():
    log = []

    class MyProcessing(BaseProcessing):
        async def call(self, ctx: Context) -> None:
            log.append(ctx.current_node)

    pipeline = Pipeline(
        script={"flow": {"node": {PRE_RESPONSE: {"": MyProcessing()}, PRE_TRANSITION: {"": MyProcessing()}}}},
        start_label=("flow", "node"),
    )
    ctx = await pipeline._run_pipeline(Message(text=""))
    assert len(log) == 2

    ctx.framework_data.current_node = None
    with pytest.raises(ContextError):
        await MyProcessing().call(ctx)
