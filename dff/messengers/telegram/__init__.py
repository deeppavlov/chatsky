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
from .messenger import (
    UpdateType,
    handler,
    message_handler,
    edited_message_handler,
    channel_post_handler,
    edited_channel_post_handler,
    inline_handler,
    chosen_inline_handler,
    callback_query_handler,
    shipping_query_handler,
    pre_checkout_query_handler,
    poll_handler,
    poll_answer_handler,
    chat_member_handler,
    my_chat_member_handler,
    chat_join_request_handler,
)
