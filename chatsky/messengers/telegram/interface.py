"""
Telegram Interfaces
-------------------
This module provides concrete implementations of the
:py:class:`~._AbstractTelegramInterface`.
"""

from pathlib import Path
from typing import Any, Optional

from chatsky.pipeline.types import PipelineRunnerFunction

from .abstract import _AbstractTelegramInterface

try:
    from telegram import Update
except ImportError:
    Update = Any


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

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(pipeline_runner, *args, **kwargs)
        self.application.run_polling(
            poll_interval=self.interval, timeout=self.timeout, allowed_updates=Update.ALL_TYPES
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

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(pipeline_runner, *args, **kwargs)
        self.application.run_webhook(listen=self.listen, port=self.port, allowed_updates=Update.ALL_TYPES)
