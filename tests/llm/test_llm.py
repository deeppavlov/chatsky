import pytest
from pydantic import BaseModel

from chatsky.llm._langchain_imports import langchain_available
from chatsky.llm.llm_api import LLM_API
from chatsky.responses.llm import LLMResponse
from chatsky.conditions.llm import LLMCondition
from chatsky.slots.llm import LLMSlot, LLMGroupSlot
from chatsky.slots.slots import SlotNotExtracted, ExtractedGroupSlot
from chatsky.llm.langchain_context import message_to_langchain, context_to_history, get_langchain_context
from chatsky.llm.prompt import Prompt, PositionConfig
from chatsky.llm.filters import IsImportant, FromModel, Return, DefaultFilter
from chatsky.llm.methods import Contains, LogProb, BaseMethod
from chatsky.core.message import Message
from chatsky.core.script import Node
from chatsky.core.node_label import AbsoluteNodeLabel

if not langchain_available:
    pytest.skip(allow_module_level=True, reason="Langchain not available.")
from chatsky.llm._langchain_imports import AIMessage, LLMResult, HumanMessage, SystemMessage
from langchain_core.outputs.chat_generation import ChatGeneration


class MockChatOpenAI:
    def __init__(self):
        self.name = "test_model"
        self.model = self

    async def ainvoke(self, history: list = [""]):
        response = AIMessage(
            content=f"Mock response with history: {[message.content[0]['text'] for message in history]}"
        )
        return response

    async def agenerate(self, history: list, logprobs=True, top_logprobs=10):
        return LLMResult(
            generations=[
                [
                    ChatGeneration(
                        message=HumanMessage(content="Mock generation without history."),
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

    def with_structured_output(self, message_schema):
        return MockedStructuredModel(root_model=message_schema)

    async def respond(self, history: list, message_schema=None):
        return self.ainvoke(history)

    async def condition(self, history: list, method: BaseMethod):
        result = await method(history, await self.model.agenerate(history, logprobs=True, top_logprobs=10))
        return result


class MockedStructuredModel:
    def __init__(self, root_model):
        self.root = root_model

    async def ainvoke(self, history):
        if isinstance(history, list):
            inst = self.root(history=history)
        else:
            # For LLMSlot
            fields = {}
            for field in self.root.model_fields:
                fields[field] = "test_data"
            inst = self.root(**fields)
        return inst

    def with_structured_output(self, message_schema):
        return message_schema


class MessageSchema(BaseModel):
    history: list[str]

    def __call__(self):
        return self.model_dump()


@pytest.fixture
def mock_structured_model():
    return MockedStructuredModel


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


class TestStructuredOutput:
    async def test_structured_output(self, monkeypatch, mock_structured_model):
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
        self.models = {
            "test_model": LLM_API(mock_model),
        }
        # self.models = {"test_model": LLM_API(mock_model)}


@pytest.fixture
def pipeline(mock_model):
    return MockPipeline(mock_model)


@pytest.fixture
def filter_context(context_factory):
    ctx = context_factory(start_label=AbsoluteNodeLabel(flow_name="flow", node_name="node"))
    ctx.framework_data.current_node = Node(misc={"prompt": "1"})
    ctx.requests[1] = Message(
        text="Request 1", misc={"important": True}, annotations={"__generated_by_model__": "test_model"}
    )
    ctx.requests[2] = Message(
        text="Request 2", misc={"important": False}, annotations={"__generated_by_model__": "other_model"}
    )
    ctx.requests[3] = Message(
        text="Request 3", misc={"important": False}, annotations={"__generated_by_model__": "test_model"}
    )
    ctx.responses[1] = Message(
        text="Response 1", misc={"important": False}, annotations={"__generated_by_model__": "test_model"}
    )
    ctx.responses[2] = Message(
        text="Response 2", misc={"important": True}, annotations={"__generated_by_model__": "other_model"}
    )
    ctx.responses[3] = Message(
        text="Response 3", misc={"important": False}, annotations={"__generated_by_model__": "test_model"}
    )
    ctx.current_turn_id = 3
    return ctx


@pytest.fixture
def context(pipeline, context_factory):
    ctx = context_factory(start_label=AbsoluteNodeLabel(flow_name="flow", node_name="node"))
    ctx.framework_data.pipeline = pipeline
    ctx.framework_data.current_node = Node(
        misc={
            "prompt": "prompt",
            "tpmorp": "absolutely not a prompt",
            "prompt_last": Prompt(message=Message("last prompt"), position=1000),
        }
    )
    for i in range(1, 4):
        ctx.requests[i] = f"Request {i}"
        ctx.responses[i] = f"Response {i}"
    ctx.requests[4] = "Last request"
    ctx.current_turn_id = 4
    return ctx


class TestMessageToLangchain:
    async def test_message_to_langchain(self, context):
        assert await message_to_langchain(Message(text="hello"), context, source="human") == HumanMessage(
            content=[{"type": "text", "text": "hello"}]
        )
        assert await message_to_langchain(Message(text="hello"), context, source="ai") == AIMessage(
            content=[{"type": "text", "text": "hello"}]
        )


class TestHistory:
    @pytest.mark.parametrize(
        "hist,expected",
        [
            (
                2,
                "Mock response with history: ['Request 2', 'Response 2', "
                "'Request 3', 'Response 3', 'prompt', 'Last request', 'last prompt']",
            ),
            (
                0,
                "Mock response with history: ['prompt', 'Last request', 'last prompt']",
            ),
            (
                4,
                "Mock response with history: ['Request 1', 'Response 1', "
                "'Request 2', 'Response 2', 'Request 3', 'Response 3', 'prompt', 'Last request', 'last prompt']",
            ),
        ],
    )
    async def test_history(self, context, pipeline, hist, expected):
        res = await LLMResponse(llm_model_name="test_model", history=hist)(context)
        assert res == Message(expected, annotations={"__generated_by_model__": "test_model"})


class TestContextToHistory:
    async def test_context_to_history(self, context):
        res = await context_to_history(
            ctx=context, length=-1, filter_func=DefaultFilter(), llm_model_name="test_model", max_size=100
        )
        expected = [
            HumanMessage(content=[{"type": "text", "text": "Request 1"}]),
            AIMessage(content=[{"type": "text", "text": "Response 1"}]),
            HumanMessage(content=[{"type": "text", "text": "Request 2"}]),
            AIMessage(content=[{"type": "text", "text": "Response 2"}]),
            HumanMessage(content=[{"type": "text", "text": "Request 3"}]),
            AIMessage(content=[{"type": "text", "text": "Response 3"}]),
        ]
        assert res == expected
        res = await context_to_history(
            ctx=context, length=1, filter_func=DefaultFilter(), llm_model_name="test_model", max_size=100
        )
        expected = [
            HumanMessage(content=[{"type": "text", "text": "Request 3"}]),
            AIMessage(content=[{"type": "text", "text": "Response 3"}]),
        ]
        assert res == expected

    async def test_context_with_response_to_history(self, filter_context):
        res = await context_to_history(
            ctx=filter_context, length=-1, filter_func=DefaultFilter(), llm_model_name="test_model", max_size=100
        )
        expected = [
            HumanMessage(content=[{"type": "text", "text": "Request 1"}]),
            AIMessage(content=[{"type": "text", "text": "Response 1"}]),
            HumanMessage(content=[{"type": "text", "text": "Request 2"}]),
            AIMessage(content=[{"type": "text", "text": "Response 2"}]),
        ]
        assert res == expected


class TestGetLangchainContext:
    @pytest.mark.parametrize(
        "cfg,expected,prompt_misc_filter",
        [
            (
                PositionConfig(),
                [
                    SystemMessage(content=[{"type": "text", "text": "system prompt"}]),
                    HumanMessage(content=[{"type": "text", "text": "Request 1"}]),
                    AIMessage(content=[{"type": "text", "text": "Response 1"}]),
                    HumanMessage(content=[{"type": "text", "text": "Request 2"}]),
                    AIMessage(content=[{"type": "text", "text": "Response 2"}]),
                    HumanMessage(content=[{"type": "text", "text": "Request 3"}]),
                    AIMessage(content=[{"type": "text", "text": "Response 3"}]),
                    HumanMessage(content=[{"type": "text", "text": "prompt"}]),
                    HumanMessage(content=[{"type": "text", "text": "call prompt"}]),
                    HumanMessage(content=[{"type": "text", "text": "Last request"}]),
                    HumanMessage(content=[{"type": "text", "text": "last prompt"}]),
                ],
                None,
            ),
            (
                PositionConfig(
                    system_prompt=10,
                    last_turn=0,
                    misc_prompt=1,
                    history=2,
                ),
                [
                    HumanMessage(content=[{"type": "text", "text": "Last request"}]),
                    HumanMessage(content=[{"type": "text", "text": "prompt"}]),
                    HumanMessage(content=[{"type": "text", "text": "Request 1"}]),
                    AIMessage(content=[{"type": "text", "text": "Response 1"}]),
                    HumanMessage(content=[{"type": "text", "text": "Request 2"}]),
                    AIMessage(content=[{"type": "text", "text": "Response 2"}]),
                    HumanMessage(content=[{"type": "text", "text": "Request 3"}]),
                    AIMessage(content=[{"type": "text", "text": "Response 3"}]),
                    HumanMessage(content=[{"type": "text", "text": "call prompt"}]),
                    SystemMessage(content=[{"type": "text", "text": "system prompt"}]),
                    HumanMessage(content=[{"type": "text", "text": "last prompt"}]),
                ],
                None,
            ),
            (
                PositionConfig(
                    system_prompt=1,
                    last_turn=1,
                    misc_prompt=1,
                    history=1,
                    call_prompt=1,
                ),
                [
                    SystemMessage(content=[{"type": "text", "text": "system prompt"}]),
                    HumanMessage(content=[{"type": "text", "text": "Request 1"}]),
                    AIMessage(content=[{"type": "text", "text": "Response 1"}]),
                    HumanMessage(content=[{"type": "text", "text": "Request 2"}]),
                    AIMessage(content=[{"type": "text", "text": "Response 2"}]),
                    HumanMessage(content=[{"type": "text", "text": "Request 3"}]),
                    AIMessage(content=[{"type": "text", "text": "Response 3"}]),
                    HumanMessage(content=[{"type": "text", "text": "absolutely not a prompt"}]),
                    HumanMessage(content=[{"type": "text", "text": "call prompt"}]),
                    HumanMessage(content=[{"type": "text", "text": "Last request"}]),
                ],
                "tpmorp",
            ),
        ],
    )
    async def test_get_langchain_context(self, context, cfg, expected, prompt_misc_filter):
        res = await get_langchain_context(
            system_prompt=Message(text="system prompt"),
            ctx=context,
            call_prompt=Prompt(message=Message(text="call prompt")),
            position_config=cfg,
            prompt_misc_filter=prompt_misc_filter if prompt_misc_filter else r"prompt",
            length=-1,
            filter_func=DefaultFilter(),
            llm_model_name="test_model",
            max_size=100,
        )

        assert res == expected

    async def test_context_with_response(self, context):
        context.responses[4] = "Last response"

        res = await get_langchain_context(
            system_prompt=Message(text="system prompt"),
            ctx=context,
            call_prompt=Prompt(message=Message(text="call prompt")),
            length=-1,
            filter_func=DefaultFilter(),
            llm_model_name="test_model",
            max_size=100,
        )

        expected = [
            SystemMessage(content=[{"type": "text", "text": "system prompt"}]),
            HumanMessage(content=[{"type": "text", "text": "Request 1"}]),
            AIMessage(content=[{"type": "text", "text": "Response 1"}]),
            HumanMessage(content=[{"type": "text", "text": "Request 2"}]),
            AIMessage(content=[{"type": "text", "text": "Response 2"}]),
            HumanMessage(content=[{"type": "text", "text": "Request 3"}]),
            AIMessage(content=[{"type": "text", "text": "Response 3"}]),
            HumanMessage(content=[{"type": "text", "text": "prompt"}]),
            HumanMessage(content=[{"type": "text", "text": "call prompt"}]),
            HumanMessage(content=[{"type": "text", "text": "Last request"}]),
            AIMessage(content=[{"type": "text", "text": "Last response"}]),
            HumanMessage(content=[{"type": "text", "text": "last prompt"}]),
        ]
        assert res == expected


class TestConditions:
    async def test_conditions(self, context):
        cond1 = LLMCondition(
            llm_model_name="test_model",
            prompt=Message("test_prompt"),
            method=Contains(pattern="history"),
        )
        cond2 = LLMCondition(
            llm_model_name="test_model",
            prompt=Message("test_prompt"),
            method=Contains(pattern="abrakadabra"),
        )
        assert await cond1(ctx=context)
        assert not await cond2(ctx=context)


class TestFilters:
    async def test_is_important_filter(self, filter_context):
        filter_func = IsImportant()
        ctx = filter_context

        assert filter_func(ctx, await ctx.requests[1], await ctx.responses[1], "test_model") == Return.Request
        assert filter_func(ctx, await ctx.requests[2], await ctx.responses[2], "test_model") == Return.Response
        assert filter_func(ctx, await ctx.requests[3], await ctx.responses[3], "test_model") == Return.NoReturn
        assert filter_func(ctx, None, await ctx.responses[1], "test_model") == Return.NoReturn
        assert filter_func(ctx, await ctx.requests[1], None, "test_model") == Return.Request

    async def test_model_filter(self, filter_context):
        filter_func = FromModel()
        ctx = filter_context

        assert filter_func(ctx, await ctx.requests[1], await ctx.responses[1], "test_model") == Return.Turn
        assert filter_func(ctx, await ctx.requests[2], await ctx.responses[2], "test_model") == Return.NoReturn
        assert filter_func(ctx, await ctx.requests[3], await ctx.responses[3], "test_model") == Return.Turn
        assert filter_func(ctx, await ctx.requests[2], await ctx.responses[3], "test_model") == Return.Turn
        assert filter_func(ctx, await ctx.requests[3], await ctx.responses[2], "test_model") == Return.NoReturn


class TestBaseMethod:
    async def test_base_method(self, llmresult):
        c = Contains(pattern="")
        assert c.model_result_to_text(llmresult) == "this is a very IMPORTANT message"


class TestContainsMethod:
    async def test_contains_method(self, filter_context, llmresult):
        ctx = filter_context
        c = Contains(pattern="important")
        assert await c(ctx, llmresult)
        c = Contains(pattern="test")
        assert not await c(ctx, llmresult)


class TestLogProbMethod:
    async def test_logprob_method(self, filter_context, llmresult):
        ctx = filter_context
        c = LogProb(target_token="false", threshold=0.3)
        assert await c(ctx, llmresult)
        c = LogProb(target_token="true", threshold=0.3)
        assert not await c(ctx, llmresult)


class TestSlots:
    async def test_llm_slot(self, pipeline, context):
        slot = LLMSlot(caption="test_caption", llm_model_name="test_model")
        context.current_turn_id = 5
        # Test empty request
        context.requests[5] = ""
        assert isinstance(await slot.extract_value(context), SlotNotExtracted)

        # Test normal request
        context.requests[5] = "test request"
        result = await slot.extract_value(context)
        assert isinstance(result, str)

    async def test_llm_group_slot(self, pipeline, context):
        slot = LLMGroupSlot(
            llm_model_name="test_model",
            name=LLMSlot(caption="Extract person's name"),
            age=LLMSlot(caption="Extract person's age"),
            nested=LLMGroupSlot(llm_model_name="test_model", city=LLMSlot(caption="Extract person's city")),
        )

        context.current_turn_id = 5
        context.requests[5] = "John is 25 years old and lives in New York"
        result = await slot.get_value(context)

        assert isinstance(result, ExtractedGroupSlot)

        print(f"Extracted result: {result}")

        assert result.name.extracted_value == "test_data"
        assert result.age.extracted_value == "test_data"
        assert result.nested.city.extracted_value == "test_data"
