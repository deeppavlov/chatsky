"""
Telegram Message
--------------
This module implements inherited classes :py:module:`dff.script.core.message` modified for usage with Telegram.
"""
from typing import Optional, Union

from telebot import types

from dff.script.core.message import Message, Location, Keyboard, DataModel, root_validator, ValidationError


class TelegramUI(Keyboard):
    is_inline: bool = True
    row_width: int = 3

    @root_validator
    def validate_buttons(cls, values):
        if not values.get("is_inline"):
            for button in values.get("buttons"):
                if button.payload is not None or button.source is not None:
                    raise ValidationError(f"`payload` and `source` are only used for inline keyboards: {button}")
        return values


class RemoveKeyboard(DataModel):
    """Pass an instance of this class to :py:attr:`~.TelegramMessage.ui` to remove current keyboard."""
    ...


class TelegramMessage(Message):
    class Config:
        smart_union = True
    ui: Optional[Union[TelegramUI, RemoveKeyboard, types.ReplyKeyboardRemove, types.ReplyKeyboardMarkup, types.InlineKeyboardMarkup]] = None
    location: Optional[Location] = None
