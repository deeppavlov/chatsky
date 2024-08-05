from chatsky.llm.wrapper import LLM_API, llm_condition, llm_response, message_to_langchain
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from chatsky.script.core.message import Message
from chatsky.script import Context
from chatsky.pipeline import Pipeline

import pytest

def test_message_to_langchain():
    assert message_to_langchain(Message(text="hello")) == HumanMessage(content=[{'type': 'text', 'text': 'hello'}])
    assert message_to_langchain(Message(text="hello")) != HumanMessage(content=[{'type': 'text', 'text': 'goodbye'}])
    assert message_to_langchain(Message(text="hello"), human=False) != HumanMessage(content=[{'type': 'text', 'text': 'hello'}])
    assert message_to_langchain(Message(text="hello"), human=False) == AIMessage(content=[{'type': 'text', 'text': 'hello'}])


@pytest.fixture
def mock_model(self):
    class MockChatOpenAI:
        self.model = self
        self.name = "test_model"
        def respond(self, history: list = [""]):
            return AIMessage(content=f"Mock response with history: {history}")
    
    return MockChatOpenAI()

@pytest.fixture
def context():
    class MockContext(Context):
        def __init__(self):
            self.requests = [Message(text=f"Request {i}") for i in range(10)]
            self.responses = [Message(text=f"Response {i}") for i in range(10)]
            self.last_request = Message(text="Last request")
    return MockContext()

@pytest.fixture
def pipeline(mock_model):
    class MockPipeline(Pipeline):
        def __init__(self):
            self.models = {"test_model": LLM_API(mock_model)}

    return MockPipeline()

def test_history():
    pass