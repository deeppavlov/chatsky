# -*- coding: utf-8 -*-

try:
    import telebot
except ImportError:
    raise ImportError("telebot is not installed. Run `pip install dff[telegram]`")

from .messenger import TelegramMessenger
from .interface import PollingTelegramInterface, CallbackTelegramInterface
from .message import TelegramUI, TelegramMessage, RemoveKeyboard, ParseMode
from .messenger import (
    UpdateType,
    telegram_condition,
)
