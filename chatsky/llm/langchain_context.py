"""
LLM Utils.
----------
The Utils module contains functions for converting Chatsky's objects to an LLM_API and langchain compatible versions.
"""

import re
import logging
from typing import Literal, Union

from chatsky.core.context import Context
from chatsky.core.message import Message
from chatsky.core.script_function import ConstResponse
from chatsky.llm._langchain_imports import HumanMessage, SystemMessage, AIMessage, check_langchain_available
from chatsky.llm.filters import BaseHistoryFilter
from chatsky.llm.prompt import Prompt, DesaultPositionConfig


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
    if isinstance(message, str):
        message = Message(text=message)
    if isinstance(message, ConstResponse):
        message = message.root

    if message.text is None:
        content = []
    elif len(message.text) > max_size:
        logging.warning("Message is too long.")
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
    ctx: Context, length: int, filter_func: BaseHistoryFilter, model_name: str, max_size: int
) -> list[HumanMessage | AIMessage | SystemMessage]:
    """
    Convert context to list of langchain messages.

    :param ctx: Current dialog context.
    :param length: Amount of turns to include in history. Set to `-1` to include all context.
    :param filter_func: Function to filter the context.
    :param model_name: name of the model from the pipeline.
    :param max_size: Maximum size of the message in symbols.

    :return: List of Langchain message objects.
    """
    history = []

    pairs = zip(
        [ctx.requests[x] for x in range(1, len(ctx.requests) + 1)],
        [ctx.responses[x] for x in range(1, len(ctx.responses) + 1)],
    )
    logging.debug(f"Dialogue turns: {pairs}")
    pairs_list = list(pairs)
    filtered_pairs = filter(
        lambda x: filter_func(ctx, x[0], x[1], model_name), pairs_list[-length:] if length != -1 else pairs_list
    )

    for req, resp in filtered_pairs:
        logging.debug(f"This pair is valid: {req, resp}")
        history.append(await message_to_langchain(req, ctx=ctx, max_size=max_size))
        history.append(await message_to_langchain(resp, ctx=ctx, source="ai", max_size=max_size))
    return history


# get a list of messages to pass to LLM from context and prompts
# called in LLM_API
async def get_langchain_context(
    system_prompt: Prompt,
    ctx: Context,
    call_prompt,
    prompt_misc_filter: str = r"prompt",  # r"prompt" -> extract misc prompts
    postition_config: DesaultPositionConfig = DesaultPositionConfig(),
    **history_args,
) -> list[HumanMessage | AIMessage | SystemMessage]:
    """
    Get a list of Langchain messages using the context and prompts.
    """
    history = context_to_history(ctx, history_args)
    prompts = [(system_prompt, system_prompt.position)]
    misc_prompts = []

    for element in ctx.current_node.misc:
        if re.match(prompt_misc_filter, element):
            misc_prompts.append(ctx.current_node.misc[element], ctx.current_node.misc[element].position)

    misc_prompts.append(call_prompt)
    prompts.extend(misc_prompts)

    for prompt in prompts:
        if prompt[1] is not None:
            prompt[1] = postition_config.get_position(prompt[1])

    prompts = sorted(prompts, key=lambda x: x.position)

    logging.debug(f"Sorted prompts: {prompts}")

    # merge prompts and history
    langchain_context = []
    for prompt in prompts:
        langchain_context.append(await message_to_langchain(prompt, ctx, source="system"))

    langchain_context.extend(history)
    return langchain_context