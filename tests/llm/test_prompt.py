import pytest
from typing import Any, Dict, List, Union
from unittest.mock import AsyncMock

from chatsky.core import BaseResponse, Context, Message
from chatsky.core.ctx_utils import FrameworkData
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.script import Node
from chatsky.llm._langchain_imports import AIMessage, HumanMessage, SystemMessage
from chatsky.llm.example_selector import StaticExampleSelector
from chatsky.llm.langchain_context import get_langchain_context
from chatsky.llm.prompt import BasePrompt, FewShotExamplePrompt, PositionConfig, Prompt


class DummyPrompt(BasePrompt):
    async def to_langchain_messages(
        self, ctx: Context
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        return []


class BrokenPrompt(BasePrompt):
    async def to_langchain_messages(
        self, ctx: Context
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        raise NotImplementedError


@pytest.fixture
def book_context(context_factory):
    ctx = context_factory(
        start_label=AbsoluteNodeLabel(flow_name="book", node_name="start")
    )
    ctx.current_turn_id = 42
    node = Node(misc={})
    ctx.framework_data = FrameworkData(current_node=node)
    ctx.requests[42] = Message('{"book_title": "1984", "author": "George Orwell"}')
    ctx.responses[42] = Message(
        '{"summary": "A dystopian novel about totalitarian regime."}'
    )
    ctx.current_turn_id = 42
    return ctx


@pytest.fixture(name="ctx")
def ctx() -> Context:
    ctx = Context()
    ctx.current_turn_id = 42
    ctx.requests = AsyncMock()
    ctx.requests.get = AsyncMock(
        return_value=Message('{"book_title": "1984", "author": "George Orwell"}')
    )
    ctx.responses = AsyncMock()
    ctx.responses.get = AsyncMock(
        return_value=Message(
            '{"summary": "A dystopian novel about totalitarian regime."}'
        )
    )
    return ctx


# --------------------
# Tests for BasePrompt
# --------------------
class TestBasePrompt:
    def test_position(self):
        prompt = DummyPrompt(position=2.0)
        assert prompt.position == 2.0

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "init_value,expected_text",
        [
            (Message("hello"), "hello"),
            ("hi there!", "hi there!"),
        ],
    )
    async def test_init_prompt_message(self, ctx, init_value, expected_text):
        prompt = Prompt(message=init_value)
        msg = await prompt.message(ctx)
        assert isinstance(msg, Message)
        assert msg.text == expected_text


# --------------------
# Tests for Prompt
# --------------------
class TestPrompt:
    @pytest.mark.asyncio
    async def test_init_with_message(self, ctx):
        raw_msg = Message("hello")
        prompt = Prompt(message=raw_msg)
        res = await prompt.message(ctx)
        assert res == raw_msg

    @pytest.mark.asyncio
    async def test_init_with_str(self, ctx):
        prompt = Prompt("hello")
        res = await prompt.message(ctx)
        assert isinstance(res, Message)
        assert res.text == "hello"

    def test_position(self):
        prompt = Prompt("data", position=3)
        assert prompt.position == 3

    @pytest.mark.asyncio
    async def test_to_langchain_messages(self, ctx, monkeypatch):
        captured: Dict[str, Any] = {}

        async def fake_message_to_langchain(msg, ctx_arg, **kwargs):
            captured["msg"] = msg
            captured["ctx"] = ctx_arg
            return HumanMessage(
                content=[{"type": "text", "text": f"Processed: {msg.text}"}]
            )

        monkeypatch.setattr(
            "chatsky.llm.langchain_context.message_to_langchain",
            fake_message_to_langchain,
        )

        prompt = Prompt("What is the capital of France?")
        result = await prompt.to_langchain_messages(ctx)

        assert result == [
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Processed: What is the capital of France?",
                    }
                ]
            )
        ]
        assert captured["msg"].text == "What is the capital of France?"
        assert captured["ctx"] is ctx

    @pytest.mark.asyncio
    async def test_prompt_with_base_response(self, ctx, monkeypatch):
        mock_response = AsyncMock(spec=BaseResponse)
        mock_response.return_value = Message(
            text="Summarize the text: 'The sun rises in the east.'"
        )

        async def fake_message_to_langchain(msg, ctx_arg, **kwargs):
            assert msg.text.startswith("Summarize the text")
            return HumanMessage(content=[{"type": "text", "text": msg.text.upper()}])

        monkeypatch.setattr(
            "chatsky.llm.langchain_context.message_to_langchain",
            fake_message_to_langchain,
        )

        prompt = Prompt(message=mock_response)
        result = await prompt.to_langchain_messages(ctx)

        assert isinstance(result[0], HumanMessage)
        assert "SUMMARIZE" in result[0].content[0]["text"]


# ------------------------------
# Tests for FewShotExamplePrompt
# ------------------------------
class TestFewShotExamplePrompt:
    @pytest.mark.asyncio
    async def test_template_and_examples(self, ctx, monkeypatch):
        examples = [
            {"input": "2 + 2", "output": "4"},
            {"input": "3 + 3", "output": "6"},
        ]
        selector = StaticExampleSelector(examples)

        async def fake_convert(msg, ctx_arg, source=None):
            return SystemMessage(content=[{"type": "text", "text": msg.text}])

        monkeypatch.setattr(
            "chatsky.llm.langchain_context.message_to_langchain",
            fake_convert,
        )

        prompt = FewShotExamplePrompt(
            template="Query: {input}\nAnswer: {output}",
            examples=selector,
            prefix="Answer the following:",
            suffix="Let's begin!",
        )

        result = await prompt.to_langchain_messages(ctx)

        assert isinstance(result[0], SystemMessage)
        assert "Query: 2 + 2" in result[0].content[0]["text"]
        assert "Answer: 4" in result[0].content[0]["text"]
        assert "Answer the following:" in result[0].content[0]["text"]

    @pytest.mark.asyncio
    async def test_examples_only(self, ctx):
        examples = [
            {"input": "10 - 3", "output": "7"},
            {"input": "5 * 5", "output": "25"},
        ]
        selector = StaticExampleSelector(examples)
        prompt = FewShotExamplePrompt(examples=selector)

        result = await prompt.to_langchain_messages(ctx)

        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "10 - 3"
        assert result[1].content == "7"
        assert result[2].content == "5 * 5"
        assert result[3].content == "25"

    @pytest.mark.asyncio
    async def test_no_examples_returns_empty(self, ctx):
        prompt = FewShotExamplePrompt()
        result = await prompt.to_langchain_messages(ctx)
        assert result == []

    @pytest.mark.asyncio
    async def test_ctx_missing_request(ctx, monkeypatch):
        ctx.current_turn_id = 42
        ctx.requests = AsyncMock()
        ctx.requests.get = AsyncMock(return_value=None)

        examples = [{"input": "First letter `Apple`?", "output": "A"}]
        selector = StaticExampleSelector(examples)
        prompt = FewShotExamplePrompt(examples=selector)

        called_args = {}

        async def fake_to_langchain_context(ex, variables):
            called_args["vars"] = variables
            return [
                HumanMessage(content="First letter `Apple`?"),
                AIMessage(content="A"),
            ]

        monkeypatch.setattr(
            "chatsky.llm.prompt.to_langchain_context",
            fake_to_langchain_context,
        )

        result = await prompt.to_langchain_messages(ctx)

        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "First letter `Apple`?"
        assert called_args["vars"]["input"] == ""

    @pytest.mark.asyncio
    async def test_message_to_langchain_error(ctx, monkeypatch):
        async def fail_convert(*args, **kwargs):
            raise RuntimeError("conversion failed")

        monkeypatch.setattr(
            "chatsky.llm.langchain_context.message_to_langchain", fail_convert
        )

        prompt = Prompt("broken")

        with pytest.raises(RuntimeError):
            await prompt.to_langchain_messages(ctx)

    @pytest.mark.asyncio
    async def test_template_without_prefix_suffix(self, ctx, monkeypatch):
        examples = [
            {"input": "1 + 1", "output": "2"},
            {"input": "2 + 2", "output": "4"},
        ]
        selector = StaticExampleSelector(examples)

        async def fake_convert(msg, ctx_arg, source=None):
            return SystemMessage(content=msg.text)

        monkeypatch.setattr(
            "chatsky.llm.langchain_context.message_to_langchain", fake_convert
        )

        prompt = FewShotExamplePrompt(
            template="Query: {input} Answer: {output}",
            examples=selector,
            prefix="",
            suffix="",
        )
        result = await prompt.to_langchain_messages(ctx)
        assert isinstance(result[0], SystemMessage)
        assert "Query: 1 + 1 Answer: 2" in result[0].content


# ------------------------
# Tests Prompt Integration
# ------------------------
class TestPromptIntegration:
    @pytest.mark.asyncio
    async def test_langchain_context_respects_position(self, book_context):
        book_context.current_node.misc = {
            "prompt_misc": Prompt("book_prompt", position=None)
        }

        position_config = PositionConfig(
            system_prompt=3,
            history=2,
            misc_prompt=0,
            call_prompt=1,
            last_turn=4,
        )

        result = await get_langchain_context(
            system_prompt=Message("System info"),
            ctx=book_context,
            call_prompt=Prompt("Call prompt"),
            position_config=position_config,
            length=-1,
            filter_func=lambda ctx, req, res, model: True,
            llm_model_name="test_model",
            max_size=100,
        )

        expected = [
            HumanMessage(content=[{"type": "text", "text": "book_prompt"}]),
            HumanMessage(content=[{"type": "text", "text": "Call prompt"}]),
            SystemMessage(content=[{"type": "text", "text": "System info"}]),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": '{"book_title": "1984", "author": "George Orwell"}',
                    }
                ]
            ),
            AIMessage(
                content=[
                    {
                        "type": "text",
                        "text": '{"summary": "A dystopian novel about totalitarian regime."}',
                    }
                ]
            ),
        ]
        assert result == expected
