"""
Telegram Message
--------------
This module implements inherited classes :py:module:`dff.script.core.message` modified for usage with Telegram.
"""
from typing import Optional, Union

from telebot import types

from dff.script.core.message import Message, Location, Keyboard


class TelegramUI(Keyboard):
    is_inline: bool = True
    row_width: int = 3


class TelegramMessage(Message):
    ui: Optional[Union[TelegramUI, types.ReplyKeyboardRemove, types.ReplyKeyboardMarkup, types.InlineKeyboardMarkup]] = None
    location: Optional[Location] = None
