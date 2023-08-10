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

from dff.script.core.message import Message, Location, Keyboard, DataModel
from pydantic import model_validator


class TelegramUI(Keyboard):
    is_inline: bool = True
    """
    Whether to use `inline keyboard <https://core.telegram.org/bots/features#inline-keyboards>`__ or
    a `keyboard <https://core.telegram.org/bots/features#keyboards>`__.
    """
    row_width: int = 3
    """Limits the maximum number of buttons in a row."""

    @model_validator(mode="after")
    def validate_buttons(self, _):
        if not self.is_inline:
            for button in self.buttons:
                if button.payload is not None or button.source is not None:
                    raise AssertionError(f"`payload` and `source` are only used for inline keyboards: {button}")
        return self


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
    """Parse mode of the message."""

    def __eq__(self, other):
        if isinstance(other, Message):
            for field in self.model_fields:
                if field not in ("parse_mode", "update_id", "update", "update_type"):
                    if field not in other.model_fields:
                        return False
                    if self.__getattribute__(field) != other.__getattribute__(field):
                        return False
            return True
        return NotImplemented
