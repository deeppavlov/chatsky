"""
Telegram Interfaces
-------------------
This module provides concrete implementations of the
:py:class:`~._AbstractTelegramInterface`.
"""

from asyncio import get_event_loop
from pathlib import Path
from typing import Any, Optional

from .abstract import _AbstractTelegramInterface

try:
    from telegram import Update
    from telegram.error import TelegramError

except ImportError:
    Update = Any
    TelegramError = Any


class LongpollingInterface(_AbstractTelegramInterface):
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

    def error_callback(self, exc: TelegramError) -> None:
        get_event_loop().create_task(self.application.process_error(error=exc, update=None))

    async def updater_coroutine(self):
        await self.application.updater.start_polling(
            poll_interval=self.interval,
            timeout=self.timeout,
            allowed_updates=Update.ALL_TYPES,
            error_callback=self.error_callback,
        )


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

    async def updater_coroutine(self):
        await self.application.updater.start_webhook(
            listen=self.listen,
            port=self.port,
            allowed_updates=Update.ALL_TYPES,
        )
