"""
Prompt position
---------------
This module provides utils for changing the default prompt positions.
"""

from typing import Optional, Union, List, Dict, Any
from abc import ABC, abstractmethod

from pydantic import BaseModel, model_validator, Field
from langchain_core.prompts import FewShotPromptTemplate

from chatsky.core import BaseResponse, AnyResponse, MessageInitTypes, Message, Context
from chatsky.llm._langchain_imports import HumanMessage, SystemMessage, AIMessage
from chatsky.llm.langchain_context import message_to_langchain


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
    """
    Position for this prompt.
    If set to None, will fallback to either :py:attr:`~PositionConfig.system_prompt`,
    :py:attr:`~PositionConfig.misc_prompt`, :py:attr:`~PositionConfig.call_prompt`
    depending on where the type of this prompt.
    """

    @abstractmethod
    async def message(self, ctx: Context) -> Message:
        """
        Get the message content for this prompt.

        :param ctx: Current dialog context.
        :return: Message object containing the prompt content.
        """
        raise NotImplementedError

    async def to_langchain_messages(
        self, 
        ctx: Context, 
        source: str = "human",
        position_config: Optional[PositionConfig] = None
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
        """
        Convert this prompt to a list of Langchain messages.

        :param ctx: Current dialog context.
        :param source: Source of the message ["human", "ai", "system"]. Defaults to "human".
        :param position_config: Configuration for positioning different parts of the context.
            If None, will use default PositionConfig().
        :return: List of Langchain message objects.
        """
        message = await self.message(ctx)
        if message.text == "":
            return []
            
        langchain_message = await message_to_langchain(message, ctx, source=source)
        return [langchain_message]


class Prompt(BasePrompt):
    """
    LLM Prompt.
    Provides position config and allow validating prompts from message or string.
    
    This class implements BasePrompt interface and provides concrete implementation
    for converting various message types (string, Message, BaseResponse) into a Message object.
    """

    message: AnyResponse
    """
    The message content of the prompt. Can be:
    - string: will be converted to Message with text field
    - Message: will be used as is
    - BaseResponse: will be evaluated in the context to get Message
    """

    def __init__(self, message: Union[MessageInitTypes, BaseResponse], position: Optional[float] = None):
        """
        Initialize a new Prompt.

        :param message: The message content for this prompt
        :param position: Optional position in the context sequence
        """
        super().__init__(message=message, position=position)

    @model_validator(mode="before")
    @classmethod
    def validate_from_message(cls, data):
        """
        Validate and convert input data to proper format.
        Allows creating Prompt from string, Message or BaseResponse directly.

        :param data: Input data to validate
        :return: Validated data in proper format
        """
        if isinstance(data, (str, Message, BaseResponse)):
            return {"message": data}
        return data

    async def message(self, ctx: Context) -> Message:
        """
        Get the message content for this prompt.
        Implements the abstract method from BasePrompt.

        :param ctx: Current dialog context
        :return: Message object containing the prompt content
        :raises ValueError: If message cannot be converted to proper format
        """
        try:
            if isinstance(self.message, Message):
                return self.message
            elif isinstance(self.message, BaseResponse):
                return await self.message(ctx)
            else:
                return Message(text=str(self.message))
        except Exception as e:
            raise ValueError(f"Failed to get message content: {str(e)}")


class FewShotExamplePrompt(BasePrompt):
    """
    Prompt class that supports few-shot examples with templates.
    Uses Langchain's example selectors and prompt templates for few-shot learning.
    """

    template: str = Field(
        ...,
        description="Template string that defines the structure of each example. Supports {variable} placeholders."
    )

    examples: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of example dictionaries. Each must include values for all variables used in the template."
    )

    example_selector: Optional[Any] = Field(
        None,
        description="Optional LangChain example selector to dynamically choose examples at runtime."
    )

    prefix: Optional[str] = Field(
        None,
        description="Text to prepend before the examples (e.g., instruction or context)."
    )

    suffix: Optional[str] = Field(
        None,
        description="Text to append after the examples (e.g., user query or final input)."
    )

    def __init__(
        self,
        template: str,
        examples: Optional[List[Dict[str, Any]]] = None,
        example_selector: Optional[Any] = None,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
        position: Optional[float] = None,
    ):
        """
        Initialize a new FewShotExamplePrompt.

        :param template: Template string for the prompt
        :param examples: List of example dictionaries
        :param example_selector: Optional example selector from Langchain
        :param prefix: Optional prefix text before examples
        :param suffix: Optional suffix text after examples
        :param position: Optional position in the context sequence
        """
        super().__init__(position=position)
        self.template = template
        self.examples = examples or []
        self.example_selector = example_selector
        self.prefix = prefix
        self.suffix = suffix

    async def message(self, ctx: Context) -> Message:
        """
        Get the message content for this prompt.
        Implements the abstract method from BasePrompt.

        :param ctx: Current dialog context
        :return: Message object containing the prompt content
        """
        try:

            
            # Create prompt template
            prompt_template = FewShotPromptTemplate(
                examples=self.examples,
                example_selector=self.example_selector,
                example_prompt=self.template,
                prefix=self.prefix,
                suffix=self.suffix,
            )
            
            # Format the prompt with context variables
            formatted_prompt = prompt_template.format(**ctx.variables)
            
            return Message(text=formatted_prompt)
        except Exception as e:
            raise ValueError(f"Failed to format few-shot prompt: {str(e)}")