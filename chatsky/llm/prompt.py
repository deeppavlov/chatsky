"""
Prompt position
---------------
This module provides utils for changing the default prompt positions.
"""

from typing import Optional, Union

from pydantic import BaseModel, model_validator

from chatsky.core import BaseResponse, AnyResponse, MessageInitTypes, Message


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


class Prompt(BaseModel):
    """
    LLM Prompt.
    Provides position config and allow validating prompts from message or string.
    """

    message: AnyResponse
    position: Optional[float] = None
    """
    Position for this prompt.
    If set to None, will fallback to either :py:attr:`~PositionConfig.system_prompt`,
    :py:attr:`~PositionConfig.misc_prompt`, :py:attr:`~PositionConfig.call_prompt`
    depending on where the type of this prompt.
    """

    def __init__(self, message: Union[MessageInitTypes, BaseResponse], position: Optional[float] = None):
        super().__init__(message=message, position=position)

    @model_validator(mode="before")
    @classmethod
    def validate_from_message(cls, data):
        if isinstance(data, (str, Message, BaseResponse)):
            return {"message": data}
        return data
