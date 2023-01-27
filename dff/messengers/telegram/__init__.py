# -*- coding: utf-8 -*-
# flake8: noqa: F401

try:
    import telebot
except ImportError:
    raise ImportError("telebot is not installed. Run `pip install dff[telegram]`")

from .messenger import TelegramMessenger
from .interface import PollingTelegramInterface, CallbackTelegramInterface
from .message import TelegramUI, TelegramMessage, RemoveKeyboard
from dff.script.core.message import Location, Attachment, Audio, Video, Image, Document, Attachments, Button, Command
