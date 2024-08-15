from chatsky.llm.wrapper import LLM_API, llm_response, message_to_langchain, __attachment_to_content
from chatsky.llm.filters import IsImportant, FromTheModel
from langchain_core.messages import HumanMessage, AIMessage
from chatsky.script.core.message import Message, Image
from chatsky.script import Context, TRANSITIONS, RESPONSE
from chatsky.script import conditions as cnd
from chatsky.pipeline import Pipeline

import pytest


class MockChatOpenAI:
    def __init__(self):
        self.name = "test_model"
        self.model = self

    def invoke(self, history: list = [""]):
        response = AIMessage(content=f"Mock response with history: {history}")
        return response

    def respond(self, history: list = [""]):
        return self.invoke(history)


@pytest.fixture
def mock_model():
    return MockChatOpenAI()

@pytest.fixture
def filter_context():
    ctx = Context()
    ctx.add_request(Message(text="Request 1", misc={"important": True}, annotation={"__generated_by_model__": "test_model"}))
    ctx.add_request(Message(text="Request 2", misc={"important": False}, annotation={"__generated_by_model__": "other_model"}))
    ctx.add_request(Message(text="Request 3", misc={"important": False}, annotation={"__generated_by_model__": "test_model"}))
    ctx.add_response(Message(text="Response 1", misc={"important": False}, annotation={"__generated_by_model__": "test_model"}))
    ctx.add_response(Message(text="Response 2", misc={"important": True}, annotation={"__generated_by_model__": "other_model"}))
    ctx.add_response(Message(text="Response 3", misc={"important": False}, annotation={"__generated_by_model__": "test_model"}))
    return ctx

@pytest.fixture
def context():
    ctx = Context()
    for i in range(3):
        ctx.add_request(Message(text=f"Request {i}"))
        ctx.add_response(Message(text=f"Response {i}"))
    ctx.add_request(Message(text="Last request"))
    return ctx


class MockPipeline:
    def __init__(self, mock_model):
        self.models = {"test_model": LLM_API(mock_model)}

@pytest.fixture
def pipeline(mock_model):
    return MockPipeline(mock_model)


def test_message_to_langchain():
    assert message_to_langchain(Message(text="hello"), source="human") == HumanMessage(content=[{"type": "text", "text": "hello"}])
    assert message_to_langchain(Message(text="hello"), source="ai") != HumanMessage(
        content=[{"type": "text", "text": "hello"}]
    )
    assert message_to_langchain(Message(text="hello"), source="ai") == AIMessage(
        content=[{"type": "text", "text": "hello"}]
    )

# @pytest.mark.parametrize("img,expected", [(Image(source="https://example.com"), ValueError)])
# def test_attachments(img, expected):
#     script = {"flow": {"node": {RESPONSE: Message(), TRANSITIONS: {"node": cnd.true()}}}}
#     pipe = Pipeline.from_script(script=script, start_label=("flow", "node"))
#     assert __attachment_to_content(img, pipe.messenger_interface) == expected


@pytest.mark.parametrize(
    "hist,expected",
    [
        (
            2,
            r"""Mock response with history: [HumanMessage(content=[{'type': 'text', 'text': 'Request 1'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 1'}]), HumanMessage(content=[{'type': 'text', 'text': 'Request 2'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 2'}]), HumanMessage(content=[{'type': 'text', 'text': 'Last request'}])]""",
        ),
        (
            0,
            r"""Mock response with history: [HumanMessage(content=[{'type': 'text', 'text': 'Last request'}])]""",
        ),
        (
            4,
            r"""Mock response with history: [HumanMessage(content=[{'type': 'text', 'text': 'Request 0'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 0'}]), HumanMessage(content=[{'type': 'text', 'text': 'Request 1'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 1'}]), HumanMessage(content=[{'type': 'text', 'text': 'Request 2'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 2'}]), HumanMessage(content=[{'type': 'text', 'text': 'Last request'}])]""",
        ),
    ],
)
def test_history(context, pipeline, hist, expected):
    assert llm_response("test_model", history=hist)(context, pipeline).text == expected


def test_is_important_filter(filter_context):
    filter_func = IsImportant()
    ctx = filter_context

    # Test filtering important messages
    assert filter_func(ctx, ctx.requests[0], ctx.responses[0], model_name="test_model")
    assert filter_func(ctx, ctx.requests[1], ctx.responses[1], model_name="test_model")
    assert not filter_func(ctx, ctx.requests[2], ctx.responses[2], model_name="test_model")

    assert not filter_func(ctx, None, ctx.responses[0], model_name="test_model")
    assert filter_func(ctx, ctx.requests[0], None, model_name="test_model")


def test_model_filter(filter_context):
    filter_func = FromTheModel()
    ctx = filter_context
    # Test filtering important messages
    assert filter_func(ctx, ctx.requests[0], ctx.responses[0], model_name="test_model")
    assert not filter_func(ctx, ctx.requests[1], ctx.responses[1], model_name="test_model")
    assert filter_func(ctx, ctx.requests[2], ctx.responses[2], model_name="test_model")
    assert filter_func(ctx, ctx.requests[1], ctx.responses[2], model_name="test_model")