"""
Telegram Interfaces
-------------------
This module provides concrete implementations of the
:py:class:`~._AbstractTelegramInterface`.
"""

from pathlib import Path
from typing import Any, Optional

from chatsky.script import Message

from chatsky.messengers.common import PollingMessengerInterface

from chatsky.pipeline.types import PipelineRunnerFunction

from .abstract import _AbstractTelegramInterface

try:
    from telegram.ext import MessageHandler, CallbackQueryHandler
    from telegram.ext.filters import ALL

    telegram_available = True
except ImportError:
    telegram_available = False

try:
    from telegram import Update
except ImportError:
    Update = Any


class LongpollingInterface(_AbstractTelegramInterface, PollingMessengerInterface):
    """
    Telegram messenger interface, that requests Telegram API in a loop.

    :param token: The Telegram bot token.
    :param attachments_directory: The directory for storing attachments.
    :param interval: A time interval between polls (in seconds).
    :param timeout: Timeout in seconds for long polling.
    """

    def __init__(
        self, token: str, attachments_directory: Optional[Path] = None, interval: int = 2, timeout: int = 20
    ) -> None:
        super().__init__(token, attachments_directory)
        self.interval = interval
        self.timeout = timeout

    async def _get_updates(self) -> list[tuple[Any, Message]]:
        updates = self.application.bot.get_updates(
            poll_interval=self.interval, timeout=self.timeout, allowed_updates=Update.ALL_TYPES
        )
        parsed_updates = []
        for update in updates:
            data_available = update.message is not None or update.callback_query is not None
            if update.effective_chat is not None and data_available:
                message = self.extract_message_from_telegram(update)
                message.original_message = update
                parsed_updates.append((update.effective_chat.id, message))
        return parsed_updates

    async def _respond(self, ctx_id, last_response):
        if last_response is not None:
            await self.cast_message_to_telegram_and_send(self.application.bot, ctx_id, last_response)


class WebhookInterface(_AbstractTelegramInterface):
    """
    Telegram messenger interface, that brings a special webserver up
    and registers up for listening for Telegram updates.

    :param token: The Telegram bot token.
    :param attachments_directory: The directory for storing attachments.
    :param host: Local host name (or IP address).
    :param port: Local port for running Telegram webhook.
    """

    def __init__(
        self, token: str, attachments_directory: Optional[Path] = None, host: str = "localhost", port: int = 844
    ):
        super().__init__(token, attachments_directory)
        self.listen = host
        self.port = port
        self.application.add_handler(MessageHandler(ALL, self.on_message))
        self.application.add_handler(CallbackQueryHandler(self.on_callback))

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(pipeline_runner, *args, **kwargs)
        self.application.run_webhook(listen=self.listen, port=self.port, allowed_updates=Update.ALL_TYPES)
