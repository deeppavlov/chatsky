"""
Telegram Message
----------------
This module implements inherited classes :py:mod:`dff.script.core.message` modified for usage with Telegram.
"""
from typing import Optional, Union
from enum import Enum

from telebot.types import (
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    Message as tlMessage,
    InlineQuery,
    ChosenInlineResult,
    CallbackQuery as tlCallbackQuery,
    ShippingQuery,
    PreCheckoutQuery,
    Poll,
    PollAnswer,
    ChatMemberUpdated,
    ChatJoinRequest,
)

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


class _ClickButton(DataModel):
    """This class is only used in telegram tests (to click buttons as a client)."""

    button_index: int


class RemoveKeyboard(DataModel):
    """Pass an instance of this class to :py:attr:`~.TelegramMessage.ui` to remove current keyboard."""

    ...


class ParseMode(Enum):
    """
    Parse mode of the message.
    More info: https://core.telegram.org/bots/api#formatting-options.
    """

    HTML = "HTML"
    MARKDOWN = "MarkdownV2"


class TelegramMessage(Message):
    class Config:
        smart_union = True

    ui: Optional[
        Union[TelegramUI, RemoveKeyboard, ReplyKeyboardRemove, ReplyKeyboardMarkup, InlineKeyboardMarkup]
    ] = None
    location: Optional[Location] = None
    callback_query: Optional[Union[str, _ClickButton]] = None
    update: Optional[
        Union[
            tlMessage,
            InlineQuery,
            ChosenInlineResult,
            tlCallbackQuery,
            ShippingQuery,
            PreCheckoutQuery,
            Poll,
            PollAnswer,
            ChatMemberUpdated,
            ChatJoinRequest,
        ]
    ] = None
    """This field stores an update representing this message."""
    update_id: Optional[int] = None
    update_type: Optional[str] = None
    """Name of the field that stores an update representing this message."""
    parse_mode: Optional[ParseMode] = None
    """Parse mode of the message"""

    def __eq__(self, other):
        if isinstance(other, Message):
            for field in self.__fields__:
                if field not in ("parse_mode", "update_id", "update", "update_type"):
                    if field not in other.__fields__:
                        return False
                    if self.__getattribute__(field) != other.__getattribute__(field):
                        return False
            return True
        return NotImplemented
