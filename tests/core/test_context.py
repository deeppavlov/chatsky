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

    def test_raises_on_empty_labels(self, ctx):
        with pytest.raises(ContextError):
            ctx.add_label(("flow", "node"))

        with pytest.raises(ContextError):
            ctx.last_label

    def test_existing_labels(self, ctx):
        ctx.labels = {5: AbsoluteNodeLabel.model_validate(("flow", "node1"))}

        assert ctx.last_label == AbsoluteNodeLabel(flow_name="flow", node_name="node1")
        ctx.add_label(("flow", "node2"))
        assert ctx.labels == {
            5: AbsoluteNodeLabel(flow_name="flow", node_name="node1"),
            6: AbsoluteNodeLabel(flow_name="flow", node_name="node2"),
        }
        assert ctx.last_label == AbsoluteNodeLabel(flow_name="flow", node_name="node2")


class TestRequests:
    @pytest.fixture
    def ctx(self, context_factory):
        return context_factory(forbidden_fields=["labels", "responses"])

    def test_existing_requests(self, ctx):
        ctx.requests = {5: Message(text="text1")}
        assert ctx.last_request == Message(text="text1")
        ctx.add_request("text2")
        assert ctx.requests == {5: Message(text="text1"), 6: Message(text="text2")}
        assert ctx.last_request == Message(text="text2")

    def test_empty_requests(self, ctx):
        with pytest.raises(ContextError):
            ctx.last_request

        ctx.add_request("text")
        assert ctx.last_request == Message(text="text")
        assert list(ctx.requests.keys()) == [1]


class TestResponses:
    @pytest.fixture
    def ctx(self, context_factory):
        return context_factory(forbidden_fields=["labels", "requests"])

    def test_existing_responses(self, ctx):
        ctx.responses = {5: Message(text="text1")}
        assert ctx.last_response == Message(text="text1")
        ctx.add_response("text2")
        assert ctx.responses == {5: Message(text="text1"), 6: Message(text="text2")}
        assert ctx.last_response == Message(text="text2")

    def test_empty_responses(self, ctx):
        assert ctx.last_response is None

        ctx.add_response("text")
        assert ctx.last_response == Message(text="text")
        assert list(ctx.responses.keys()) == [1]


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
