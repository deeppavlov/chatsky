"""
Prompt position
---------------
This module provides utils for changing the default prompt positions.
"""

from typing import Optional, Union, List, Dict, Any
from abc import ABC, abstractmethod

from pydantic import BaseModel, model_validator, Field
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from chatsky.core import BaseResponse, AnyResponse, MessageInitTypes, Message, Context

class PositionConfig(BaseModel):
    """
    Configuration for prompts position.
    Lower number prompts will go before higher number prompts in the LLM history.
    """
    system_prompt: float = 0
    history: float = 1
    misc_prompt: float = 2
    call_prompt: float = 3
    last_turn: float = 4


class BasePrompt(BaseModel, ABC):
    """
    Base class for all prompts. Provides common interface for getting Langchain messages.
    """
    @abstractmethod
    async def to_langchain_messages(
        self, 
        ctx: Context, 
        source: str = "human"
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        """
        Convert this prompt to a list of Langchain messages.
        """
        raise NotImplementedError


class Prompt(BasePrompt):
    """
    LLM Prompt.
    Provides position config and allow validating prompts from message or string.
    
    This class implements BasePrompt interface and provides concrete implementation
    for converting various message types (string, Message, BaseResponse) into a Message object.
    """

    message: AnyResponse
    position: Optional[float] = None
    """
    The message content of the prompt. Can be:
    - string: will be converted to Message with text field
    - Message: will be used as is
    - BaseResponse: will be evaluated in the context to get Message
    """

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
        source: str = "human"
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        from chatsky.llm.langchain_context import message_to_langchain
        if isinstance(self.message, BaseResponse):
            msg = await self.message(ctx)

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
    position: Optional[float] = None

    def __init__(
        self,
        template: str,
        examples: Optional[List[Dict[str, Any]]] = None,
        example_selector: Optional[Any] = None,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
        position: Optional[float] = None,
    ):
        super().__init__(
            template=template,
            examples=examples or [],
            example_selector=example_selector,
            prefix=prefix,
            suffix=suffix,
            position=position
        )

    async def to_langchain_messages(
        self,
        ctx: Context,
        source: str = "human"
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        
        example_prompt = PromptTemplate(
            input_variables=["input", "output"],
            template=self.template
        )
        # Создаём шаблон промпта
        prompt_template = FewShotPromptTemplate(
            examples=self.examples,
            example_selector=self.example_selector,
            example_prompt=example_prompt,
            prefix=self.prefix,
            suffix=self.suffix,
        )
        
        # todo:
        # msg = Message(text=ctx)
        # langchain_msg = await message_to_langchain(msg, ctx=ctx, source=source)
        # return [langchain_msg]