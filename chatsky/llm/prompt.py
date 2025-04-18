"""
Prompt position
---------------
This module provides utils for changing the default prompt positions.
"""
import re
import logging
from typing import Optional, Union, List, Dict, Any
from abc import ABC, abstractmethod

from pydantic import BaseModel, model_validator, Field
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from chatsky.core import BaseResponse, AnyResponse, MessageInitTypes, Message, Context
from chatsky.llm._langchain_imports import HumanMessage, AIMessage, SystemMessage, check_langchain_available
from chatsky.llm.langchain_context import message_to_langchain, context_to_history


logger = logging.getLogger(__name__)


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
        source: str = "human"
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
        source: str = "human"
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:

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
        source: str = "human"
    ) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:

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


async def get_langchain_context(
    system_prompt: Message,
    ctx: Context,
    call_prompt: BasePrompt,
    prompt_misc_filter: str = r"prompt", # r"prompt" -> extract misc prompts
    position_config: PositionConfig = PositionConfig(),
    **history_args,
) -> list[Union[HumanMessage, AIMessage, SystemMessage]]:
    """
    Get a list of Langchain messages using the context and prompts.

    :param system_prompt: System message to be included in the context.
    :param ctx: Current dialog context.
    :param call_prompt: Prompt to be used for the current call.
    :param prompt_misc_filter: Regex pattern to filter miscellaneous prompts from context.
        Defaults to r"prompt".
    :param position_config: Configuration for positioning different parts of the context.
        Defaults to default PositionConfig().
    :param history_args: Additional arguments to be passed to context_to_history function.

    :return: List of Langchain message objects ordered by their position values.
    """
    check_langchain_available()
    logger.debug(f"History args: {history_args}")

    history = await context_to_history(ctx, **history_args)
    logger.debug(f"Position config: {position_config}")
    prompts: list[tuple[list[Union[HumanMessage, AIMessage, SystemMessage]], float]] = []

    if system_prompt.text != "":
        prompts.append(
            ([await message_to_langchain(system_prompt, ctx, source="system")], position_config.system_prompt)
        )
    prompts.append((history, position_config.history))

    logger.debug(f"System prompt: {prompts[0]}")

    for element_name, element in ctx.current_node.misc.items():
        if re.compile(prompt_misc_filter).match(element_name):

            prompt = BasePrompt.model_validate(element)
            prompt_messages = await prompt.to_langchain_messages(ctx)

            prompts.append(
                (
                    prompt_messages,
                    prompt.position if prompt.position is not None else position_config.misc_prompt,
                )
            )

    call_prompt_messages = await call_prompt.to_langchain_messages(ctx)
    if call_prompt_messages:
        prompts.append(
            (
                call_prompt_messages,
                call_prompt.position if call_prompt.position is not None else position_config.call_prompt,
            )
        )

    last_turn_request = await ctx.requests.get(ctx.current_turn_id)
    last_turn_response = await ctx.responses.get(ctx.current_turn_id)

    if last_turn_request:
        prompts.append(
            ([await message_to_langchain(last_turn_request, ctx, source="human")], position_config.last_turn)
        )
    if last_turn_response:
        prompts.append(([await message_to_langchain(last_turn_response, ctx, source="ai")], position_config.last_turn))

    logger.debug(f"Prompts: {prompts}")
    prompts = sorted(prompts, key=lambda x: x[1])

    # flatten prompts list
    langchain_context = []
    for message_block in prompts:
        langchain_context.extend(message_block[0])

    return langchain_context
