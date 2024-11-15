from chatsky.llm.llm_api import LLM_API
from chatsky.responses.llm import LLMResponse
from chatsky.llm.utils import message_to_langchain, attachment_to_content
from chatsky.llm.filters import IsImportant, FromTheModel
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel
from chatsky.core.message import Message, Image
from chatsky.core.context import Context
from chatsky.core.script import Node
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky import (
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
)

from chatsky.messengers.common import MessengerInterfaceWithAttachments

import pytest


class MockChatOpenAI:
    def __init__(self):
        self.name = "test_model"
        self.model = self

    async def ainvoke(self, history: list = [""]):
        response = AIMessage(content=f"Mock response with history: {[message.content[0]['text'] for message in history]}")
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
        return {"history": self.history}


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


class MockMessengerInterface(MessengerInterfaceWithAttachments):
    async def connect(self):
        pass

    async def get_attachment_bytes(self, attachment):
        return b"mock_bytes"


@pytest.mark.parametrize(
    "img,expected",
    [
        (
            Image(
                source="https://raw.githubusercontent.com/deeppavlov/chatsky/master/docs/source/_static/images/Chatsky-full-dark.svg"
            ),
            "data:image/svg;base64,PHN2ZyB3aWR0aD0iMTM3OCIgaGVpZ2h0PSIyNzYiIHZpZXdCb3g9IjAgMCAxMzc4IDI3NiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTE0NCAxMDguMDE5SDIyOC4wNDhDMjY3LjQ3NCAxMDguMDE5IDMwNi4zNTkgOTguODg4IDM0MS42MjMgODEuMzQ5N0MzNTAuMDY2IDc3LjE1MDcgMzYwIDgzLjI1NzUgMzYwIDkyLjY0NjlWMTA4LjAxOUMzNjAgMTg3LjEyNSAyOTUuNTI5IDI1MS4yNTMgMjE2IDI1MS4yNTNIMTE1LjM1NEMxMDYuMDQ5IDI1MS4yNTMgMTAxLjM5NiAyNTEuMjUzIDk2LjgwNzkgMjUxLjU0NUM4MC42NzU4IDI1Mi41NzEgNjQuODMyNSAyNTYuMjkxIDQ5Ljk0MjMgMjYyLjU1QzQ1LjcwNzMgMjY0LjMzIDQxLjU0NTggMjY2LjM5OSAzMy4yMjI4IDI3MC41MzlMMzIuMTk5NCAyNzEuMDQ4QzI2LjgwNDggMjczLjczMSAyNC4xMDc1IDI3NS4wNzIgMjEuOTg5OCAyNzUuNTUxQzEyLjQwOTcgMjc3LjcxNyAyLjg1MzA3IDI3MS44NDIgMC41MTY0ODggMjYyLjM1QzAgMjYwLjI1MiAwIDI1Ny4yNTIgMCAyNTEuMjUzQzAgMTcyLjE0NyA2NC40NzEgMTA4LjAxOSAxNDQgMTA4LjAxOVoiIGZpbGw9IiMwMEEzRkYiLz4KPHBhdGggZD0iTTI1MC4zNjQgMEMyODkuMjkxIDAgMzIzLjA0MSAyMi41MDUzIDMzOS41NjkgNTUuMzk4N0MzNDAuMDk1IDU2Ljc4ODQgMzQwLjI0MyA1OS4wNjQ3IDMzOS40MTUgNjEuNjg1NEMzMzguNjIxIDY0LjE5NjUgMzM3LjI3OCA2NS45MjM0IDMzNi4wODkgNjYuNzg3NEMzMDEuOTM0IDgzLjM2NTYgMjY0LjMxNiA5MiAyMjYuMTY3IDkySDE3MC4zNTdDMTU5Ljc5MyA5MiAxNTguMDExIDkxLjcwMzYgMTU2LjI5OCA5MC42MzgxQzE1NS45MDIgOTAuMzkyMyAxNTQuOTc4IDg5LjYwMzUgMTUzLjk3NSA4OC4yNzVDMTUyLjk3MyA4Ni45NDY1IDE1Mi40NjQgODUuODM2OSAxNTIuMzMzIDg1LjM4NjRDMTUxLjcyNiA4My4yODg3IDE1MS43OTQgODIuMjEwNCAxNTMuODY2IDc0LjUxNjhDMTY1LjQzNSAzMS41NjU0IDIwNC4yNjggMCAyNTAuMzY0IDBaIiBmaWxsPSIjRkZBRDBEIi8+CjxwYXRoIGQ9Ik01MDAuMDAxIDIxOEM0OTAuOCAyMTggNDgyLjMzNCAyMTYuNjc0IDQ3NC42IDIxNC4wMjJDNDY3IDIxMS4zNyA0NjAuNCAyMDcuMjYgNDU0LjggMjAxLjY5MUM0NDkuMiAxOTUuOTg5IDQ0NC44IDE4OC42MyA0NDEuNiAxNzkuNjEzQzQzOC41MzMgMTcwLjU5NyA0MzcgMTU5LjcyNCA0MzcgMTQ2Ljk5NFYxNDMuMDE3QzQzNyAxMzAuODE4IDQzOC42IDEyMC40MDkgNDQxLjggMTExLjc5QzQ0NS4xMzMgMTAzLjAzOSA0NDkuNiA5NS44Nzg1IDQ1NS4yIDkwLjMwOTRDNDYwLjkzNCA4NC43NDAzIDQ2Ny42IDgwLjYyOTggNDc1LjIgNzcuOTc3OUM0ODIuOTM0IDc1LjMyNiA0OTEuMiA3NCA1MDAuMDAxIDc0QzUwNy44NjcgNzQgNTE1LjI2NyA3NC45MjgyIDUyMi4yMDEgNzYuNzg0NUM1MjkuMTM0IDc4LjY0MDkgNTM1LjIwMSA4MS41NTggNTQwLjQwMSA4NS41MzU5QzU0NS43MzQgODkuMzgxMiA1NTAuMDAxIDk0LjM1MzYgNTUzLjIwMSAxMDAuNDUzQzU1Ni41MzQgMTA2LjU1MiA1NTguNDY4IDExMy43NzkgNTU5LjAwMSAxMjIuMTMzSDUyNy44MDFDNTI2LjMzNCAxMTQuMTc3IDUyMy4xMzQgMTA4LjM0MyA1MTguMjAxIDEwNC42M0M1MTMuMjY3IDEwMC45MTcgNTA3LjIwMSA5OS4wNjA4IDUwMC4wMDEgOTkuMDYwOEM0OTUuODY3IDk5LjA2MDggNDkxLjg2NyA5OS43OTAxIDQ4OCAxMDEuMjQ5QzQ4NC4yNjcgMTAyLjcwNyA0ODAuOTM0IDEwNS4xNiA0NzggMTA4LjYwOEM0NzUuMDY3IDExMi4wNTUgNDcyLjY2NyAxMTYuNTY0IDQ3MC44IDEyMi4xMzNDNDY5LjA2NyAxMjcuNzAyIDQ2OC4yIDEzNC42NjMgNDY4LjIgMTQzLjAxN1YxNDYuOTk0QzQ2OC4yIDE1NS43NDYgNDY5LjEzNCAxNjMuMTA1IDQ3MSAxNjkuMDcyQzQ3Mi44NjcgMTc0LjkwNiA0NzUuMjY3IDE3OS42MTMgNDc4LjIgMTgzLjE5M0M0ODEuMjY3IDE4Ni42NDEgNDg0LjY2NyAxODkuMTYgNDg4LjQgMTkwLjc1MUM0OTIuMjY3IDE5Mi4yMSA0OTYuMTM0IDE5Mi45MzkgNTAwLjAwMSAxOTIuOTM5QzUwNy42MDEgMTkyLjkzOSA1MTMuODY3IDE5MS4wMTcgNTE4LjgwMSAxODcuMTcxQzUyMy43MzQgMTgzLjE5MyA1MjYuNzM0IDE3Ny40MjUgNTI3LjgwMSAxNjkuODY3SDU1OS4wMDFDNTU4LjMzNCAxNzguNjE5IDU1Ni40MDEgMTg2LjA0NCA1NTMuMjAxIDE5Mi4xNDRDNTUwLjAwMSAxOTguMjQzIDU0NS44MDEgMjAzLjIxNSA1NDAuNjAxIDIwNy4wNjFDNTM1LjQwMSAyMTAuOTA2IDUyOS4zMzQgMjEzLjY5MSA1MjIuNDAxIDIxNS40MTRDNTE1LjQ2NyAyMTcuMTM4IDUwOC4wMDEgMjE4IDUwMC4wMDEgMjE4WiIgZmlsbD0iIzAwQTNGRiIvPgo8cGF0aCBkPSJNNTgzLjA0IDc2LjM4NjdINjEzLjA0MVYxMzEuNjhINjczLjA0MVY3Ni4zODY3SDcwMy4wNDFWMjE1LjYxM0g2NzMuMDQxVjE1Ni4zNDNINjEzLjA0MVYyMTUuNjEzSDU4My4wNFY3Ni4zODY3WiIgZmlsbD0iIzAwQTNGRiIvPgo8cGF0aCBkPSJNODEyLjU5NSAxODcuMTcxSDc2MC43OTVMNzUwLjE5NSAyMTUuNjEzSDcyMC45OTVMNzcyLjk5NSA3Ni4zODY3SDgwMi45OTVMODU0Ljk5NiAyMTUuNjEzSDgyMy4zOTVMODEyLjU5NSAxODcuMTcxWk03NjkuOTk1IDE2Mi41MDhIODAzLjU5NUw3ODYuNzk1IDExNC4xNzdMNzY5Ljk5NSAxNjIuNTA4WiIgZmlsbD0iIzAwQTNGRiIvPgo8cGF0aCBkPSJNODkyLjAxOSAxMDEuMDVIODQ3LjAxOVY3Ni4zODY3SDk2Ny4wMlYxMDEuMDVIOTIyLjAyVjIxNS42MTNIODkyLjAxOVYxMDEuMDVaIiBmaWxsPSIjMDBBM0ZGIi8+CjxwYXRoIGQ9Ik0xMDM1Ljk3IDIxOEMxMDE3LjQ0IDIxOCAxMDAzLjQ0IDIxNC4yMjEgOTkzLjk3MyAyMDYuNjYzQzk4NC41MDcgMTk5LjEwNSA5NzkuNTA3IDE4OS4xNiA5NzguOTczIDE3Ni44MjlIMTAwOC45N0MxMDA5LjUxIDE3OS40ODEgMTAxMC4zMSAxODEuODAxIDEwMTEuMzcgMTgzLjc5QzEwMTIuNDQgMTg1Ljc3OSAxMDE0LjA0IDE4Ny40MzYgMTAxNi4xNyAxODguNzYyQzEwMTguMzEgMTkwLjA4OCAxMDIwLjk3IDE5MS4xNDkgMTAyNC4xNyAxOTEuOTQ1QzEwMjcuMzcgMTkyLjYwOCAxMDMxLjMxIDE5Mi45MzkgMTAzNS45NyAxOTIuOTM5QzEwNDUuNTcgMTkyLjkzOSAxMDUyLjQ0IDE5MS42OCAxMDU2LjU3IDE4OS4xNkMxMDYwLjg0IDE4Ni41MDggMTA2Mi45NyAxODIuNzk2IDEwNjIuOTcgMTc4LjAyMkMxMDYyLjk3IDE3Mi4xODggMTA2MC4xNyAxNjcuODEyIDEwNTQuNTcgMTY0Ljg5NUMxMDQ5LjExIDE2MS44NDUgMTA0MC4zMSAxNTkuMTI3IDEwMjguMTcgMTU2Ljc0QzEwMjAuOTcgMTU1LjQxNCAxMDE0LjU3IDE1My42OTEgMTAwOC45NyAxNTEuNTY5QzEwMDMuMzcgMTQ5LjMxNSA5OTguNjQgMTQ2LjUzIDk5NC43NzMgMTQzLjIxNUM5OTAuOTA3IDEzOS43NjggOTg3Ljk3MyAxMzUuNjU3IDk4NS45NzMgMTMwLjg4NEM5ODMuOTczIDEyNi4xMSA5ODIuOTczIDEyMC40MDkgOTgyLjk3MyAxMTMuNzc5Qzk4Mi45NzMgMTA3LjgxMiA5ODQuMTczIDEwMi4zNzYgOTg2LjU3MyA5Ny40Njk2Qzk4OS4xMDcgOTIuNTYzNSA5OTIuNjQgODguMzg2NyA5OTcuMTczIDg0LjkzOTJDMTAwMS44NCA4MS4zNTkxIDEwMDcuNDQgNzguNjQwOSAxMDEzLjk3IDc2Ljc4NDVDMTAyMC41MSA3NC45MjgyIDEwMjcuODQgNzQgMTAzNS45NyA3NEMxMDQ0Ljc3IDc0IDEwNTIuMzcgNzQuOTI4MiAxMDU4Ljc3IDc2Ljc4NDVDMTA2NS4xNyA3OC42NDA5IDEwNzAuNTEgODEuMjkyOCAxMDc0Ljc3IDg0Ljc0MDNDMTA3OS4xNyA4OC4xODc4IDEwODIuNTEgOTIuMjk4MyAxMDg0Ljc3IDk3LjA3MThDMTA4Ny4wNCAxMDEuODQ1IDEwODguNDQgMTA3LjIxNSAxMDg4Ljk3IDExMy4xODJIMTA1OC45N0MxMDU4LjA0IDEwOC40MDkgMTA1NS45MSAxMDQuODk1IDEwNTIuNTcgMTAyLjY0MUMxMDQ5LjI0IDEwMC4yNTQgMTA0My43MSA5OS4wNjA4IDEwMzUuOTcgOTkuMDYwOEMxMDI4LjExIDk5LjA2MDggMTAyMi4zMSAxMDAuMzIgMTAxOC41NyAxMDIuODRDMTAxNC44NCAxMDUuMzU5IDEwMTIuOTcgMTA4Ljc0IDEwMTIuOTcgMTEyLjk4M0MxMDEyLjk3IDExOC4wMjIgMTAxNS41MSAxMjIuMDY2IDEwMjAuNTcgMTI1LjExNkMxMDI1Ljc3IDEyOC4wMzMgMTAzMy45MSAxMzAuNTUyIDEwNDQuOTcgMTMyLjY3NEMxMDUyLjU3IDEzNC4xMzMgMTA1OS4zMSAxMzUuOTIzIDEwNjUuMTcgMTM4LjA0NEMxMDcxLjE3IDE0MC4xNjYgMTA3Ni4xNyAxNDIuODg0IDEwODAuMTcgMTQ2LjE5OUMxMDg0LjMxIDE0OS41MTQgMTA4Ny40NCAxNTMuNjI0IDEwODkuNTcgMTU4LjUzQzEwOTEuODQgMTYzLjMwNCAxMDkyLjk3IDE2OS4wNzIgMTA5Mi45NyAxNzUuODM0QzEwOTIuOTcgMTg4LjY5NiAxMDg3Ljk3IDE5OC45NzIgMTA3Ny45NyAyMDYuNjYzQzEwNjguMTEgMjE0LjIyMSAxMDU0LjExIDIxOCAxMDM1Ljk3IDIxOFoiIGZpbGw9IiMwMEEzRkYiLz4KPHBhdGggZD0iTTExMTguMDEgNzYuMzg2N0gxMTQ4LjAxVjEzNS4wNjFMMTE5OS4yMSA3Ni4zODY3SDEyMzQuMDFMMTE4MS44MSAxMzMuNDdMMTIzOC4wMSAyMTUuNjEzSDEyMDIuODFMMTE2MS42MSAxNTMuMTZMMTE0OC4wMSAxNjcuODc4VjIxNS42MTNIMTExOC4wMVY3Ni4zODY3WiIgZmlsbD0iIzAwQTNGRiIvPgo8cGF0aCBkPSJNMTI5OSAxNjIuNTA4TDEyNDYgNzYuMzg2N0gxMjgxLjJMMTMxNC42IDEzMi4yNzZMMTM0NiA3Ni4zODY3SDEzNzhMMTMyOSAxNjIuNTA4VjIxNS42MTNIMTI5OVYxNjIuNTA4WiIgZmlsbD0iIzAwQTNGRiIvPgo8L3N2Zz4K",
        )
    ],
)
async def test_attachments(img, expected):
    script = {"flow": {"node": {RESPONSE: Message(), TRANSITIONS: [Tr(dst="node", cnd=True)]}}}
    pipe = Pipeline(script=script, start_label=("flow", "node"), messenger_interface=MockMessengerInterface())
    res = await attachment_to_content(img, pipe.messenger_interface)
    assert res == expected


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
    assert res.text == expected


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
    filter_func = FromTheModel()
    ctx = filter_context
    # Test filtering important messages
    assert filter_func(ctx, ctx.requests[1], ctx.responses[1], model_name="test_model")
    assert not filter_func(ctx, ctx.requests[2], ctx.responses[2], model_name="test_model")
    assert filter_func(ctx, ctx.requests[3], ctx.responses[3], model_name="test_model")
    assert filter_func(ctx, ctx.requests[2], ctx.responses[3], model_name="test_model")
