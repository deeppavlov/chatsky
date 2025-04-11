"""
Standard Responses
------------------
This module provides basic responses.
"""

import random
from typing import List

from pydantic import field_validator

from chatsky.core import BaseResponse, Message, Context
from chatsky.core.message import MessageInitTypes


class RandomChoice(BaseResponse):
    """
    Return a random message from :py:attr:`responses`.
    """

    responses: List[MessageInitTypes]
    """A list of messages to choose from."""

    @field_validator("responses", mode="before")
    def validate_responses(obj):
        return [Message.model_validate(message) for message in obj]

    async def call(self, ctx: Context) -> MessageInitTypes:
        return random.choice(self.responses)
