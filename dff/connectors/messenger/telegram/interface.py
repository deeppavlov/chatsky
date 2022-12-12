"""
Interface
------------
This module implements various interfaces for :py:class:`~dff.connectors.messenger.telegram.messenger.TelegramMessenger`
that can be used to interact with the Telegram API.
"""
from typing import Any, Optional, List, Tuple, Hashable, Callable

from telebot import types, logger

from dff.core.engine.core import Context
from dff.core.pipeline import PollingMessengerInterface, PipelineRunnerFunction, CallbackMessengerInterface
from .messenger import TelegramMessenger

flask_imported: bool
try:
    from flask import Flask, request, abort

    flask_imported = True
except ImportError:
    flask_imported = False
    Flask = Any
    request, abort = None, None


def extract_telegram_request_and_id(messenger: TelegramMessenger, update: types.Update) -> Tuple[Any, Hashable]:
    """
    Utility function that extracts parameters from a telegram update.
    Changes the messenger state, setting the last update id.

    :param messenger: Messenger instance.
    :param update: Update to process.
    """
    if update.update_id > messenger.last_update_id:
        messenger.last_update_id = update.update_id

    update_fields = vars(update).copy()
    update_fields.pop("update_id")
    inner_update = next(filter(lambda val: val is not None, list(update_fields.values())))

    ctx_id = (vars(inner_update).get("from_user")).id
    return inner_update, ctx_id


class PollingTelegramInterface(PollingMessengerInterface):
    """
    Asynchronous Telegram interface that retrieves updates by polling.
    Multi-threaded polling is currently not supported, but will be implemented in the future.

    :param messenger: :py:class:`~dff.connectors.messenger.telegram.messenger.TelegramMessenger` instance.
    :param interval: Polling interval. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_ .
    :param allowed_updates: Processed updates. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_ .
    :param timeout: General timeout. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_ .
    :param long_polling_timeout: Polling timeout. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_ .
    """

    def __init__(
        self,
        messenger: TelegramMessenger,
        interval: int = 3,
        allowed_updates: Optional[List[str]] = None,
        timeout: int = 20,
        long_polling_timeout: int = 20,
    ):
        self.messenger: TelegramMessenger = messenger
        self.interval: int = interval
        self.allowed_updates: Optional[List[str]] = allowed_updates
        self.timeout: int = timeout
        self.long_polling_timeout: int = long_polling_timeout

    def _request(self) -> List[Tuple[Any, Hashable]]:
        updates = self.messenger.get_updates(
            offset=(self.messenger.last_update_id + 1),
            allowed_updates=self.allowed_updates,
            timeout=self.timeout,
            long_polling_timeout=self.long_polling_timeout,
        )
        update_list = [extract_telegram_request_and_id(self.messenger, update) for update in updates]
        return update_list

    def _respond(self, response: List[Context]):
        for resp in response:
            self.messenger.send_response(resp.id, resp.last_response)

    def _on_exception(self, e: Exception):
        logger.error(e)
        self.messenger._TeleBot__stop_polling.set()

    async def connect(self, callback: PipelineRunnerFunction, loop: Optional[Callable] = None, *args, **kwargs):
        self.messenger._TeleBot__stop_polling.clear()
        self.messenger.get_updates(offset=-1)

        await super().connect(
            callback, loop=loop or (lambda: not self.messenger._TeleBot__stop_polling.wait(self.interval))
        )


class WebhookTelegramInterface(CallbackMessengerInterface):
    """
    Asynchronous Telegram interface that retrieves updates via webhook.
    Any Flask server can be passed to set up a webhook on a separate endpoint.

    :param messenger: :py:class:`~dff.connectors.messenger.telegram.messenger.TelegramMessenger` instance.
    :param app: Flask instance.
    :param endpoint: Webhook endpoint. Should be prefixed with "/".
    :param host: Host IP.
    :param port: Port of the app.
    :param full_uri: Full public IP of your webhook that is accessible by https.
    """

    def __init__(
        self,
        messenger: TelegramMessenger,
        app: Optional[Flask] = None,
        host: str = "localhost",
        port: int = 8443,
        endpoint: str = "/telegram-webhook",
        full_uri: Optional[str] = None,
    ):
        if not flask_imported:
            raise ModuleNotFoundError("Flask is not installed")

        self.messenger: TelegramMessenger = messenger
        self.app: Flask = app if app else Flask(__name__)
        self.host: str = host
        self.port: int = port
        self.endpoint: str = endpoint
        self.full_uri: str = full_uri or "".join([f"https://{host}:{port}", endpoint])

        async def endpoint():
            if not request.headers.get("content-type") == "application/json":
                abort(403)

            json_string = request.get_data().decode("utf-8")
            update = types.Update.de_json(json_string)
            return self.on_request(*extract_telegram_request_and_id(self.messenger, update))

        self.app.route(self.endpoint, methods=["POST"])(endpoint)

    async def connect(self, callback: PipelineRunnerFunction):
        await super().connect(callback)

        self.messenger.remove_webhook()
        self.messenger.set_webhook(self.full_uri)

        self.app.run(host=self.host, port=self.port)
