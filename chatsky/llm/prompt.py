"""
Prompt position
---------------
This module provides utils for changing the default prompt positions.
"""

from typing import Optional, Union, List, Dict, Any
from abc import ABC, abstractmethod

from pydantic import BaseModel, model_validator, Field
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from chatsky.core import BaseResponse, AnyResponse, MessageInitTypes, Message, Context
from chatsky.llm._langchain_imports import HumanMessage, AIMessage, SystemMessage


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
        ctx: Context, 
        source: str = "human",
        position_config: Optional[PositionConfig] = None
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        """
        Convert this prompt to a list of Langchain messages.
        """
        raise NotImplementedError

class Prompt(BasePrompt):
    """
    Zero‑shot prompt: wraps a string, Message or BaseResponse
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
        ctx: Context,
        source: str = "human",
        position_config: Optional[PositionConfig] = None
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        from chatsky.llm.langchain_context import message_to_langchain
        if isinstance(self.message, BaseResponse):
            msg = await self.message(ctx)
        elif isinstance(self.message, Message):
            msg = self.message
        else:
            msg = Message(text=str(self.message))

        langchain_msg = await message_to_langchain(msg, ctx, source=source)
        return [langchain_msg]


class FewShotExamplePrompt(BasePrompt):
    """
    Prompt class that supports few-shot examples with templates.
    Uses Langchain's example selectors and prompt templates for few-shot learning.
    """
    template: str = Field(...)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    example_selector: Optional[Any] = Field(None)
    prefix: Optional[str] = Field(None)
    suffix: Optional[str] = Field(None)

    async def to_langchain_messages(
        self,
        ctx: Context,
        source: str = "human",
        position_config: Optional[PositionConfig] = None
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:

        from chatsky.llm.langchain_context import message_to_langchain
        example_prompt = PromptTemplate(
            input_variables=["input", "output"],
            template=self.template
        )
        prompt_template = FewShotPromptTemplate(
            examples=self.examples,
            example_selector=self.example_selector,
            example_prompt=example_prompt,
            prefix=self.prefix,
            suffix=self.suffix,
        )

        last_req = await ctx.requests.get(ctx.current_turn_id)
        user_input = last_req.text if (last_req and last_req.text) else ""
        text = prompt_template.format(input=user_input, output="")

        msg = Message(text=text)
        langchain_msg = await message_to_langchain(msg, ctx, source=source)
        return [langchain_msg]
