import pytest
from typing import List, Union

from chatsky.llm.prompt import BasePrompt
from chatsky.core import Context
from chatsky.llm._langchain_imports import HumanMessage, SystemMessage, AIMessage


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

# --------------------
# Tests for BasePrompt
# --------------------

class TestBasePrompt:
    def test_position_can_be_set(self):
        prompt = DummyPrompt(position=2.0)
        assert prompt.position == 2.0

    @pytest.mark.asyncio
    async def test_dummy_prompt_returns_empty_list(self):
        prompt = DummyPrompt()
        messages = await prompt.to_langchain_messages(ctx=Context())
        assert messages == []

    @pytest.mark.asyncio
    async def test_broken_prompt_raises_not_implemented(self):
        prompt = BrokenPrompt()
        with pytest.raises(NotImplementedError):
            await prompt.to_langchain_messages(ctx=Context())
