from chatsky.llm.wrapper import LLM_API, llm_response, message_to_langchain, __attachment_to_content
from chatsky.llm.filters import IsImportant, FromTheModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.pydantic_v1 import BaseModel
from chatsky.core.message import Message, Image
from chatsky.core.context import Context
from chatsky.core.script import Node
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky import (
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    # all the aliases used in tutorials are available for direct import
    # e.g. you can do `from chatsky import Tr` instead
)

from chatsky.messengers.common import MessengerInterfaceWithAttachments

import pytest


class MockChatOpenAI:
    def __init__(self):
        self.name = "test_model"
        self.model = self

    async def ainvoke(self, history: list = [""]):
        response = AIMessage(content=f"Mock response with history: {history}")
        return response

    def respond(self, history: list = [""]):
        return self.ainvoke(history)

class MockedStructuredModel(MockChatOpenAI):
        root: MockChatOpenAI

        def invoke(self, history):
            return self.root(history=history)

class MessageSchema(BaseModel):
    history: list

@pytest.fixture
def mock_model():
    return MockChatOpenAI()

@pytest.fixture
def mock_structured_model():
    return MockedStructuredModel()


class MockPipeline:
    def __init__(self, mock_model):
        # self.models = {"test_model": LLM_API(mock_model), "struct_model": LLM_API(mock_structured_model)}
        self.models = {"test_model": LLM_API(mock_model)}


@pytest.fixture
def pipeline(mock_model):
    return MockPipeline(mock_model)

def test_structured_model(monkeypatch, history):
    monkeypatch.setattr(LLM_API.model, "with_structured_output", MockedStructuredModel)
    assert LLM_API.respond(message_schema=MessageSchema, history=history) == Message(f"{{history: {history}}}")

@pytest.fixture
def filter_context():
    ctx = Context.init(AbsoluteNodeLabel(flow_name="flow", node_name="node"))
    ctx.framework_data.current_node = Node(misc={"prompt": "1"})
    ctx.add_request(
        Message(text="Request 1", misc={"important": True}, annotation={"__generated_by_model__": "test_model"})
    )
    ctx.add_request(
        Message(text="Request 2", misc={"important": False}, annotation={"__generated_by_model__": "other_model"})
    )
    ctx.add_request(
        Message(text="Request 3", misc={"important": False}, annotation={"__generated_by_model__": "test_model"})
    )
    ctx.add_response(
        Message(text="Response 1", misc={"important": False}, annotation={"__generated_by_model__": "test_model"})
    )
    ctx.add_response(
        Message(text="Response 2", misc={"important": True}, annotation={"__generated_by_model__": "other_model"})
    )
    ctx.add_response(
        Message(text="Response 3", misc={"important": False}, annotation={"__generated_by_model__": "test_model"})
    )
    return ctx


@pytest.fixture
def context():
    ctx = Context.init(AbsoluteNodeLabel(flow_name="flow", node_name="node"))
    ctx.framework_data.current_node = Node(misc={"prompt": "1"})
    for i in range(3):
        ctx.add_request(f"Requestoo {i}")
        ctx.add_response(f"Responsioo {i}")
    ctx.add_request("Last request")
    return ctx

async def test_message_to_langchain(pipeline):
    assert await message_to_langchain(Message(text="hello"), pipeline, source="human") == HumanMessage(
        content=[{"type": "text", "text": "hello"}]
    )
    assert await message_to_langchain(Message(text="hello"), pipeline, source="ai") == AIMessage(
        content=[{"type": "text", "text": "hello"}]
    )


# @pytest.mark.parametrize("img,expected", [(Image(source="https://example.com"), ValueError)])
# async def test_attachments(img, expected):
#     script = {"flow": {"node": {RESPONSE: Message(), TRANSITIONS: [Tr(dst="node", cnd=True)]}}}
#     pipe = Pipeline(script=script, start_label=("flow", "node"), messenger_interface=MessengerInterfaceWithAttachments())
#     res = await __attachment_to_content(img, pipe.messenger_interface)
#     assert res == expected


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
async def test_history(context, pipeline, hist, expected):
    res = await llm_response("test_model", history=hist)(context, pipeline)
    assert res.text == expected


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
