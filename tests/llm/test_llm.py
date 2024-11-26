import pytest
from pydantic import BaseModel

from chatsky.llm._langchain_imports import langchain_available
from chatsky.llm.llm_api import LLM_API
from chatsky.responses.llm import LLMResponse
from chatsky.llm.utils import message_to_langchain, context_to_history
from chatsky.llm.filters import IsImportant, FromModel
from chatsky.llm.methods import Contains, LogProb
from chatsky.core.message import Message
from chatsky.core.context import Context
from chatsky.core.script import Node
from chatsky.core.node_label import AbsoluteNodeLabel

if not langchain_available:
    pytest.skip(allow_module_level=True, reason="Langchain not available.")
from chatsky.llm._langchain_imports import AIMessage, LLMResult, HumanMessage
from langchain_core.outputs.chat_generation import ChatGeneration

from chatsky import (
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
)


class MockChatOpenAI:
    def __init__(self):
        self.name = "test_model"
        self.model = self

    async def ainvoke(self, history: list = [""]):
        response = AIMessage(
            content=f"Mock response with history: {[message.content[0]['text'] for message in history]}"
        )
        return response

    def with_structured_output(self, message_schema):
        return MockedStructuredModel(root_model=message_schema)

    def respond(self, history: list = [""]):
        return self.ainvoke(history)


class MockedStructuredModel:
    def __init__(self, root_model):
        self.root = root_model

    async def ainvoke(self, history):
        inst = self.root(history=history)
        return inst()


class MessageSchema(BaseModel):
    history: list[str]

    def __call__(self):
        return self.model_dump()


@pytest.fixture
def mock_structured_model():
    return MockedStructuredModel


async def test_structured_output(monkeypatch, mock_structured_model):
    # Create a mock LLM_API instance
    llm_api = LLM_API(MockChatOpenAI())

    # Test data
    history = ["message1", "message2"]

    # Call the respond method
    result = await llm_api.respond(message_schema=MessageSchema, history=history)

    # Assert the result
    expected_result = Message(text='{"history":["message1","message2"]}')
    assert result == expected_result


@pytest.fixture
def mock_model():
    return MockChatOpenAI()


class MockPipeline:
    def __init__(self, mock_model):
        self.models = {"test_model": LLM_API(mock_model), "struct_model": LLM_API(mock_structured_model)}
        # self.models = {"test_model": LLM_API(mock_model)}


@pytest.fixture
def pipeline(mock_model):
    return MockPipeline(mock_model)


@pytest.fixture
def filter_context():
    ctx = Context.init(AbsoluteNodeLabel(flow_name="flow", node_name="node"))
    ctx.framework_data.current_node = Node(misc={"prompt": "1"})
    ctx.add_request(
        Message(text="Request 1", misc={"important": True}, annotations={"__generated_by_model__": "test_model"})
    )
    ctx.add_request(
        Message(text="Request 2", misc={"important": False}, annotations={"__generated_by_model__": "other_model"})
    )
    ctx.add_request(
        Message(text="Request 3", misc={"important": False}, annotations={"__generated_by_model__": "test_model"})
    )
    ctx.add_response(
        Message(text="Response 1", misc={"important": False}, annotations={"__generated_by_model__": "test_model"})
    )
    ctx.add_response(
        Message(text="Response 2", misc={"important": True}, annotations={"__generated_by_model__": "other_model"})
    )
    ctx.add_response(
        Message(text="Response 3", misc={"important": False}, annotations={"__generated_by_model__": "test_model"})
    )
    return ctx


@pytest.fixture
def context(pipeline):
    ctx = Context.init(AbsoluteNodeLabel(flow_name="flow", node_name="node"))
    ctx.framework_data.pipeline = pipeline
    ctx.framework_data.current_node = Node(misc={"prompt": "prompt"})
    for i in range(3):
        ctx.add_request(f"Request {i}")
        ctx.add_response(f"Response {i}")
    ctx.add_request("Last request")
    return ctx


async def test_message_to_langchain(context):
    assert await message_to_langchain(Message(text="hello"), context, source="human") == HumanMessage(
        content=[{"type": "text", "text": "hello"}]
    )
    assert await message_to_langchain(Message(text="hello"), context, source="ai") == AIMessage(
        content=[{"type": "text", "text": "hello"}]
    )


@pytest.mark.parametrize(
    "hist,expected",
    [
        (
            2,
            "Mock response with history: ['prompt', 'Request 1', 'Response 1', "
            "'Request 2', 'Response 2', 'Last request']",
        ),
        (
            0,
            "Mock response with history: ['prompt', 'Last request']",
        ),
        (
            4,
            "Mock response with history: ['prompt', 'Request 0', 'Response 0', "
            "'Request 1', 'Response 1', 'Request 2', 'Response 2', 'Last request']",
        ),
    ],
)
async def test_history(context, pipeline, hist, expected):
    res = await LLMResponse(model_name="test_model", history=hist)(context)
    assert res == Message(expected, annotations={"__generated_by_model__": "test_model"})


async def test_context_to_history(context):
    res = await context_to_history(
        ctx=context, length=-1, filter_func=lambda *args: True, model_name="test_model", max_size=100
    )
    expected = [
        HumanMessage(content=[{"type": "text", "text": "Request 0"}]),
        AIMessage(content=[{"type": "text", "text": "Response 0"}]),
        HumanMessage(content=[{"type": "text", "text": "Request 1"}]),
        AIMessage(content=[{"type": "text", "text": "Response 1"}]),
        HumanMessage(content=[{"type": "text", "text": "Request 2"}]),
        AIMessage(content=[{"type": "text", "text": "Response 2"}]),
    ]
    assert res == expected
    res = await context_to_history(
        ctx=context, length=1, filter_func=lambda *args: True, model_name="test_model", max_size=100
    )
    expected = [
        HumanMessage(content=[{"type": "text", "text": "Request 2"}]),
        AIMessage(content=[{"type": "text", "text": "Response 2"}]),
    ]
    assert res == expected


def test_is_important_filter(filter_context):
    filter_func = IsImportant()
    ctx = filter_context

    # Test filtering important messages
    assert filter_func(ctx, ctx.requests[1], ctx.responses[1], model_name="test_model")
    assert filter_func(ctx, ctx.requests[2], ctx.responses[2], model_name="test_model")
    assert not filter_func(ctx, ctx.requests[3], ctx.responses[3], model_name="test_model")

    assert not filter_func(ctx, None, ctx.responses[1], model_name="test_model")
    assert filter_func(ctx, ctx.requests[1], None, model_name="test_model")


def test_model_filter(filter_context):
    filter_func = FromModel()
    ctx = filter_context
    # Test filtering messages from a certain model
    assert filter_func(ctx, ctx.requests[1], ctx.responses[1], model_name="test_model")
    assert not filter_func(ctx, ctx.requests[2], ctx.responses[2], model_name="test_model")
    assert filter_func(ctx, ctx.requests[3], ctx.responses[3], model_name="test_model")
    assert filter_func(ctx, ctx.requests[2], ctx.responses[3], model_name="test_model")


@pytest.fixture
def llmresult():
    return LLMResult(
        generations=[
            [
                ChatGeneration(
                    message=HumanMessage(content="this is a very IMPORTANT message"),
                    generation_info={
                        "logprobs": {
                            "content": [
                                {
                                    "top_logprobs": [
                                        {"token": "true", "logprob": 0.1},
                                        {"token": "false", "logprob": 0.5},
                                    ]
                                }
                            ]
                        }
                    },
                )
            ]
        ]
    )


async def test_base_method(llmresult):
    c = Contains(pattern="")
    assert await c.model_result_to_text(llmresult) == "this is a very IMPORTANT message"


async def test_contains_method(filter_context, llmresult):
    ctx = filter_context
    c = Contains(pattern="important")
    assert await c(ctx, llmresult)
    c = Contains(pattern="test")
    assert not await c(ctx, llmresult)


async def test_logprob_method(filter_context, llmresult):
    ctx = filter_context
    c = LogProb(target_token="false", threshold=0.3)
    assert await c(ctx, llmresult)
    c = LogProb(target_token="true", threshold=0.3)
    assert not await c(ctx, llmresult)
