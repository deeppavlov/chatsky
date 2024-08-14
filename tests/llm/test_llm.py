from chatsky.llm.wrapper import LLM_API, llm_response, message_to_langchain, __attachment_to_content
from chatsky.llm.filters import BaseFilter, IsImportant, FromTheModel
from langchain_core.messages import HumanMessage, AIMessage
from chatsky.script.core.message import Message, Image
from pydantic import BaseModel

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


class TestFilter(BaseFilter):
    async def __call__(self, ctx=None, request: Message = None, response: Message = None, model_name: str = None):
        pass


def test_message_to_langchain():
    assert message_to_langchain(Message(text="hello")) == HumanMessage(content=[{"type": "text", "text": "hello"}])
    assert message_to_langchain(Message(text="hello")) != HumanMessage(content=[{"type": "text", "text": "goodbye"}])
    assert message_to_langchain(Message(text="hello"), human=False) != HumanMessage(
        content=[{"type": "text", "text": "hello"}]
    )
    assert message_to_langchain(Message(text="hello"), human=False) == AIMessage(
        content=[{"type": "text", "text": "hello"}]
    )


# @pytest.mark.parametrize("img,expected", [(Image(source="https://example.com"), ValueError)])
# def test_attachments(img, expected):
#     assert __attachment_to_content(img) == expected


@pytest.mark.parametrize(
    "hist,expected",
    [
        (
            2,
            r"""Mock response with history: [HumanMessage(content=[{'type': 'text', 'text': 'Request 1'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 1'}]), HumanMessage(content=[{'type': 'text', 'text': 'Request 2'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 2'}]), HumanMessage(content=[{'type': 'text', 'text': 'prompt\nLast request'}])]""",
        ),
        (
            0,
            r"""Mock response with history: [HumanMessage(content=[{'type': 'text', 'text': 'prompt\nLast request'}])]""",
        ),
        (
            4,
            r"""Mock response with history: [HumanMessage(content=[{'type': 'text', 'text': 'Request 0'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 0'}]), HumanMessage(content=[{'type': 'text', 'text': 'Request 1'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 1'}]), HumanMessage(content=[{'type': 'text', 'text': 'Request 2'}]), AIMessage(content=[{'type': 'text', 'text': 'Response 2'}]), HumanMessage(content=[{'type': 'text', 'text': 'prompt\nLast request'}])]""",
        ),
    ],
)
def test_history(context, pipeline, hist, expected):
    assert llm_response("test_model", "prompt", history=hist)(context, pipeline).text == expected


# @pytest.mark.parametrize("filter_func,expected",
#                          [(FromTheModel)])
# def test_filtering(context, pipeline, filter_func, expected):
#     llm_response("test_model", "prompt", history=5, filter_func=filter_func)(context, pipeline).text == expected
