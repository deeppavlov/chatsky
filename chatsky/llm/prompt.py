"""
Prompt position
---------------
This module provides utils for changing the default prompt positions.
"""

from abc import ABC, abstractmethod
from typing import Optional, Union, List

from pydantic import BaseModel, Field, model_validator
from langchain_core.example_selectors.base import BaseExampleSelector
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

from chatsky.core import AnyResponse, BaseResponse, Context, Message, MessageInitTypes
from chatsky.llm._langchain_imports import AIMessage, HumanMessage, SystemMessage
from chatsky.llm.example_selector import to_langchain_context

class PositionConfig(BaseModel):
    """
    Configuration for prompts position.
    Lower number prompts will go before higher number prompts in the
    LLM history.
    """
    system_prompt: float = 0
    history: float = 1
    misc_prompt: float = 2
    call_prompt: float = 3
    last_turn: float = 4


class BasePrompt(BaseModel, ABC):
    """
    Base class for all prompts.
    Provides common interface for getting Langchain messages.
    """
    position: Optional[float] = None

    @abstractmethod
    async def to_langchain_messages(
        self,
        ctx: Context
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        """
        Convert this prompt to a list of Langchain messages.
        """
        raise NotImplementedError


class Prompt(BasePrompt):
    """
    Prompt wrapper: wraps a string, Message or BaseResponse.
    """
    message: AnyResponse

    def __init__(self, message: Union[MessageInitTypes, BaseResponse], position: Optional[float] = None):
        super().__init__(message=message, position=position)

    @model_validator(mode="before")
    @classmethod
    def validate_from_message(cls, data):
        if isinstance(data, (str, Message, BaseResponse)):
            return {"message": data}
        return data

    async def to_langchain_messages(
        self,
        ctx: Context
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        from chatsky.llm.langchain_context import message_to_langchain
        msg = await self.message(ctx)

        langchain_msg = await message_to_langchain(msg, ctx)
        return [langchain_msg]


class FewShotExamplePrompt(BasePrompt):
    """
    Prompt class that supports few-shot examples with templates.
    Uses Langchain's example selectors and prompt templates for few-shot learning.
    """
    template: Optional[str] = Field(None)
    examples: Optional[BaseExampleSelector] = None
    prefix: Optional[str] = Field(None)
    suffix: Optional[str] = Field(None)

    # for unstandart type
    model_config = {"arbitrary_types_allowed": True}

    async def to_langchain_messages(
        self,
        ctx: Context
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        from chatsky.llm.langchain_context import message_to_langchain

        last_req = await ctx.requests.get(ctx.current_turn_id)
        user_input = last_req.text if (last_req and last_req.text) else ""

        # case: template + examples
        if self.template is not None and self.examples is not None:
            raw_examples = await self.examples.aselect_examples({"input": user_input})

            example_prompt = PromptTemplate(
                input_variables=["input", "output"],
                template=self.template
            )
            prompt_template = FewShotPromptTemplate(
                examples=raw_examples,
                example_prompt=example_prompt,
                prefix=self.prefix,
                suffix=self.suffix,
            )
            text = prompt_template.format(input=user_input)
            msg = Message(text=text)
            return [await message_to_langchain(msg, ctx, source="system")]

        # case: examples only
        if self.examples is not None:
            return await to_langchain_context(self.examples, {"input": user_input})

        # case: no examples
        return []
