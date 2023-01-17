# -*- coding: utf-8 -*-
# flake8: noqa: F401

try:
    import telebot
except ImportError:
    raise ImportError("telebot is not installed. Run `pip install dff[telegram]`")

from .messenger import TelegramMessenger
from .interface import PollingTelegramInterface, WebhookTelegramInterface
from .types import TelegramUI, TelegramButton, TelegramMessage
