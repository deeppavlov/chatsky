import pytest
from typing import List, Union, Dict, Any

from chatsky.llm.prompt import BasePrompt, Prompt, FewShotExamplePrompt
from chatsky.core import Message, Context
from chatsky.llm._langchain_imports import HumanMessage, SystemMessage, AIMessage
from chatsky.llm.example_selector import StaticExampleSelector


class DummyPrompt(BasePrompt):
    async def to_langchain_messages(
        self,
        ctx: Context
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        return []


class BrokenPrompt(BasePrompt):
    async def to_langchain_messages(
        self,
        ctx: Context
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        raise NotImplementedError

@pytest.fixture()
def ctx() -> Context:
    return Context()

# --------------------
# Tests for BasePrompt
# --------------------

class TestBasePrompt:
    def test_position(self):
        prompt = DummyPrompt(position=2.0)
        assert prompt.position == 2.0

    @pytest.mark.asyncio
    async def test_dummy_prompt(self):
        prompt = DummyPrompt()
        messages = await prompt.to_langchain_messages(ctx=Context())
        assert messages == []

    @pytest.mark.asyncio
    async def test_broken_prompt(self):
        prompt = BrokenPrompt()
        with pytest.raises(NotImplementedError):
            await prompt.to_langchain_messages(ctx=Context())

# --------------------
# Tests for Prompt
# --------------------
class TestPromp:
    @pytest.mark.asyncio
    async def test_init_with_message(self, ctx):
        raw_msg = Message("hi")
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
            return HumanMessage(content=[{"type": "text", "text": "Who won the World Cup in 2018?"}])

        monkeypatch.setattr(
            "chatsky.llm.langchain_context.message_to_langchain",
            fake_message_to_langchain,
        )

        prompt = Prompt("test")
        result = await prompt.to_langchain_messages(ctx)
        print('ctx', ctx)
        print('result', result)

        assert result == [
            HumanMessage(content=[{"type": "text", "text": "Who won the World Cup in 2018?"}])
        ]
        assert captured["msg"].text == "test"
        assert captured["ctx"] is ctx

# ------------------------------
# Tests for FewShotExamplePrompt
# ------------------------------
