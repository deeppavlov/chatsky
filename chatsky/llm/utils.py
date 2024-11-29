"""
LLM Utils.
----------
The Utils module contains functions for converting Chatsky's objects to an LLM_API and langchain compatible versions.
"""

import logging
from typing import Literal, Union

from chatsky.core.context import Context
from chatsky.core.message import Message
from chatsky.llm._langchain_imports import HumanMessage, SystemMessage, AIMessage, check_langchain_available
from chatsky.llm.filters import BaseHistoryFilter


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
    if length != -1:
        for req, resp in filter(lambda x: filter_func(ctx, x[0], x[1], model_name), list(pairs)[-length:]):
            logging.debug(f"This pair is valid: {req, resp}")
            history.append(await message_to_langchain(req, ctx=ctx, max_size=max_size))
            history.append(await message_to_langchain(resp, ctx=ctx, source="ai", max_size=max_size))
    else:
        # TODO: Fix redundant code
        for req, resp in filter(lambda x: filter_func(ctx, x[0], x[1], model_name), list(pairs)):
            logging.debug(f"This pair is valid: {req, resp}")
            history.append(await message_to_langchain(req, ctx=ctx, max_size=max_size))
            history.append(await message_to_langchain(resp, ctx=ctx, source="ai", max_size=max_size))
    return history
