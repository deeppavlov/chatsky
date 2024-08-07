from chatsky.llm.wrapper import LLM_API, llm_condition, llm_response, message_to_langchain
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from chatsky.script.core.message import Message
from chatsky.script import Context
from chatsky.pipeline import Pipeline
from pydantic import BaseModel

import pytest

def test_message_to_langchain():
    assert message_to_langchain(Message(text="hello")) == HumanMessage(content=[{'type': 'text', 'text': 'hello'}])
    assert message_to_langchain(Message(text="hello")) != HumanMessage(content=[{'type': 'text', 'text': 'goodbye'}])
    assert message_to_langchain(Message(text="hello"), human=False) != HumanMessage(content=[{'type': 'text', 'text': 'hello'}])
    assert message_to_langchain(Message(text="hello"), human=False) == AIMessage(content=[{'type': 'text', 'text': 'hello'}])


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

class MockContext(BaseModel):
    requests: list[Message]
    responses: list[Message]
    last_request: Message

    def __init__(self):
        super().__init__(
            requests=[Message(text=f"Request {i}") for i in range(3)],
            responses=[Message(text=f"Response {i}") for i in range(3)],
            last_request=Message(text="Last request"),
        )

class MockPipeline:
    def __init__(self, mock_model):
        self.models = {"test_model": LLM_API(mock_model)}

@pytest.fixture
def context():
    return MockContext()

@pytest.fixture
def pipeline(mock_model):
    return MockPipeline(mock_model)


def test_history(context, pipeline):
    assert llm_response("test_model", "prompt", history=2)(context, pipeline).text == r"""Mock response with history: [HumanMessage(content=[{'type': 'text', 'text': 'Request 1'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 1'}]), HumanMessage(content=[{'type': 'text', 'text': 'Request 2'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 2'}]), HumanMessage(content=[{'type': 'text', 'text': 'prompt\nLast request'}])]"""
    assert llm_response("test_model", "prompt", history=0)(context, pipeline).text == r"""Mock response with history: [HumanMessage(content=[{'type': 'text', 'text': 'prompt\nLast request'}])]"""
    assert llm_response("test_model", "prompt", history=4)(context, pipeline).text == r"""Mock response with history: [HumanMessage(content=[{'type': 'text', 'text': 'Request 0'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 0'}]), HumanMessage(content=[{'type': 'text', 'text': 'Request 1'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 1'}]), HumanMessage(content=[{'type': 'text', 'text': 'Request 2'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 2'}]), HumanMessage(content=[{'type': 'text', 'text': 'prompt\nLast request'}])]"""
