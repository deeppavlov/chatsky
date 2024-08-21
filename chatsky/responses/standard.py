"""
Standard Responses
------------------
This module provides basic responses.
"""

import random
from typing import List

from chatsky.core import BaseResponse, Message, Context
from chatsky.core.message import MessageInitTypes


class RandomChoice(BaseResponse):
    """
    Return a random message from :py:attr:`responses`.
    """

    responses: List[Message]
    """A list of messages to choose from."""

    def __init__(self, *responses: MessageInitTypes):
        super().__init__(responses=responses)

    async def call(self, ctx: Context) -> MessageInitTypes:
        return random.choice(self.responses)
