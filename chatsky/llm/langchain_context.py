"""
LLM Utils.
----------
The Utils module contains functions for converting Chatsky's objects to an LLM_API and langchain compatible versions.
"""

import re
import logging
from typing import Literal, Union
from pydantic import validate_call

from chatsky.core import AnyResponse, Context, Message
from chatsky.core.script_function import ConstResponse
from chatsky.llm._langchain_imports import HumanMessage, SystemMessage, AIMessage, check_langchain_available
from chatsky.llm.filters import BaseHistoryFilter
from chatsky.llm.prompt import Prompt, PositionConfig

logger = logging.getLogger(__name__)
logger.debug("Loaded LLM Utils logger.")

async def message_to_langchain(
    message: Message, ctx: Context, source: Literal["human", "ai", "system"] = "human", max_size: int = 1000
) -> Union[HumanMessage, AIMessage, SystemMessage]:
    """
    Create a langchain message from a :py:class:`~chatsky.script.core.message.Message` object.

    :param message: Chatsky Message to convert to Langchain Message.
    :param ctx: Current dialog context.
    :param source: Source of a message [`human`, `ai`, `system`]. Defaults to "human".
    :param max_size: Maximum size of the message in symbols.
        If exceed the limit will raise ValueError.
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
) -> list[HumanMessage | AIMessage | SystemMessage]:
    """
    Convert context to list of langchain messages.

    :param ctx: Current dialog context.
    :param length: Amount of turns to include in history. Set to `-1` to include all context.
    :param filter_func: Function to filter the context.
    :param llm_model_name: name of the model from the pipeline.
    :param max_size: Maximum size of the message in symbols.

    :return: List of Langchain message objects.
    """
    history = []

    # pairs = zip(
    #     [ctx.requests[x] for x in range(1, len(ctx.requests) + 1)],
    #     [ctx.responses[x] for x in range(1, len(ctx.responses) + 1)],
    # )
    # pairs_list = list(pairs)
    # filtered_pairs = filter(
    #     lambda x: filter_func(ctx, x[0], x[1], llm_model_name), pairs_list[-length:] if length != -1 else pairs_list
    # )

    # for req, resp in filtered_pairs:
    #     logger.debug(f"This pair is valid: {req, resp}")
    #     history.append(await message_to_langchain(req, ctx=ctx, max_size=max_size))
    #     history.append(await message_to_langchain(resp, ctx=ctx, source="ai", max_size=max_size))

    indices = range(1, min(max([*ctx.requests.keys(), 0]), max([*ctx.responses.keys(), 0]))+1)

    if length == 0:
        return []
    elif length > 0:
        indices = indices[-length:]

    # TODO:
    # Refactor this after #93 PR merge
    for turn_id in indices:
        request = ctx.requests[turn_id]
        response = ctx.responses[turn_id]
        if filter_func(ctx, request, response, llm_model_name):
            if request:
                history.append(await message_to_langchain(request, ctx=ctx, max_size=max_size))
            if response:
                history.append(await message_to_langchain(response, ctx=ctx, source="ai", max_size=max_size))

    return history


# get a list of messages to pass to LLM from context and prompts
# called in LLM_API
async def get_langchain_context(
    system_prompt: Message,
    ctx: Context,
    call_prompt: Prompt,
    prompt_misc_filter: str = r"prompt",  # r"prompt" -> extract misc prompts
    position_config: PositionConfig = PositionConfig(),
    **history_args,
) -> list[HumanMessage | AIMessage | SystemMessage]:
    """
    Get a list of Langchain messages using the context and prompts.
    """
    # TODO:
    # decide what to do with last response (it is stored in history)
    logger.debug(f"History args: {history_args}")

    history = await context_to_history(ctx, **history_args)
    logger.debug(f"Position config: {position_config}")
    prompts: list[tuple[list[Union[HumanMessage, AIMessage, SystemMessage]], float]] = [
        ([await message_to_langchain(system_prompt, ctx, source="system")], position_config.system_prompt),
        (history, position_config.history),
    ]

    logger.debug(f"System prompt: {prompts[0]}")

    for element_name, element in ctx.current_node.misc.items():
        if re.match(prompt_misc_filter, element_name):

            prompt = Prompt.model_validate(element)
            prompt_langchain_message = await message_to_langchain(await prompt.prompt(ctx), ctx, source="human")

            if prompt.position is None:
                prompt.position = position_config.misc_prompt
            prompts.append(([prompt_langchain_message], prompt.position))

    call_prompt_text = await call_prompt.prompt(ctx)
    call_prompt_message = await message_to_langchain(call_prompt_text, ctx, source="human")
    prompts.append(([call_prompt_message], call_prompt.position or position_config.call_prompt))

    prompts.append(([await message_to_langchain(ctx.last_request, ctx, source="human")], position_config.last_request))

    logger.debug(f"Prompts: {prompts}")
    prompts = sorted(prompts, key=lambda x: x[1])
    logger.debug(f"Sorted prompts: {prompts}")

    # flatten prompts list
    langchain_context = []
    for message_block in prompts:
        langchain_context.extend(message_block[0])

    return langchain_context
