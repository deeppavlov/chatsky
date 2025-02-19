"""
LLM Utils.
----------
The Utils module contains functions for converting Chatsky's objects to an LLM_API and langchain compatible versions.
"""

import re
import logging
from typing import Literal, Union
import asyncio

from chatsky.core import Context, Message
from chatsky.llm._langchain_imports import HumanMessage, SystemMessage, AIMessage, check_langchain_available
from chatsky.llm.filters import BaseHistoryFilter, Return
from chatsky.llm.prompt import Prompt, PositionConfig


logger = logging.getLogger(__name__)


async def message_to_langchain(
    message: Message, ctx: Context, source: Literal["human", "ai", "system"] = "human", max_size: int = 5000
) -> Union[HumanMessage, AIMessage, SystemMessage]:
    """
    Create a langchain message from a :py:class:`~chatsky.script.core.message.Message` object.

    :param message: Chatsky Message to convert to Langchain Message.
    :param ctx: Current dialog context.
    :param source: Source of the message [`human`, `ai`, `system`]. Defaults to "human".
    :param max_size: Maximum size of the message measured in characters.
        If a message exceeds the limit it will not be sent to the LLM and a warning
        will be produced
    """
    check_langchain_available()
    if message.text is None:
        content = []
    elif len(message.text) > max_size:
        logger.warning("Message is too long.")
        content = []
    else:
        content = [{"type": "text", "text": message.text}]

    if source == "human":
        return HumanMessage(content=content)
    elif source == "ai":
        return AIMessage(content=content)
    elif source == "system":
        return SystemMessage(content=content)
    else:
        return HumanMessage(content=content)


async def context_to_history(
    ctx: Context, length: int, filter_func: BaseHistoryFilter, llm_model_name: str, max_size: int
) -> list[Union[HumanMessage, AIMessage, SystemMessage]]:
    """
    Convert context to list of langchain messages.

    :param ctx: Current dialog context.
    :param length: Amount of turns to include in history. Set to `-1` to include all context.
    :param filter_func: Function to filter the context.
    :param llm_model_name: name of the model from the pipeline.
    :param max_size: Maximum size of the message in symbols.

    :return: List of Langchain message objects.
    """
    check_langchain_available()
    history = []
    indices = list(range(1, ctx.current_turn_id))

    if length == 0:
        return []
    elif length > 0:
        indices = indices[-length:]

    for request, response in zip(*await asyncio.gather(ctx.requests.get(indices), ctx.responses.get(indices))):
        filter_result = filter_func(ctx, request, response, llm_model_name)
        if request is not None and filter_result in (Return.Request, Return.Turn):
            history.append(await message_to_langchain(request, ctx=ctx, max_size=max_size))
        if response is not None and filter_result in (Return.Response, Return.Turn):
            history.append(await message_to_langchain(response, ctx=ctx, source="ai", max_size=max_size))

    return history


async def get_langchain_context(
    system_prompt: Message,
    ctx: Context,
    call_prompt: Prompt,
    prompt_misc_filter: str = r"prompt",  # r"prompt" -> extract misc prompts
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

            prompt = Prompt.model_validate(element)
            prompt_langchain_message = await message_to_langchain(await prompt.message(ctx), ctx, source="human")

            prompts.append(
                (
                    [prompt_langchain_message],
                    prompt.position if prompt.position is not None else position_config.misc_prompt,
                )
            )

    call_prompt_text = await call_prompt.message(ctx)
    if call_prompt_text.text != "":
        call_prompt_message = await message_to_langchain(call_prompt_text, ctx, source="human")
        prompts.append(
            (
                [call_prompt_message],
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
