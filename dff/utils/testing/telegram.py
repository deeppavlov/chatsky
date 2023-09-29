"""
Telegram testing utils
----------------------
This module defines functions used to test Telegram interface.
"""
from typing import List, Optional, cast, Tuple
from contextlib import asynccontextmanager, nullcontext
import logging
import asyncio
from tempfile import TemporaryDirectory
from pathlib import Path
from copy import deepcopy

from telethon.tl.types import ReplyKeyboardHide
from telethon import TelegramClient
from telethon.types import User
from telethon.custom import Message as TlMessage
from telebot import types

from dff.pipeline.pipeline.pipeline import Pipeline
from dff.script.core.message import Message, Attachments, Attachment, Button, Location
from dff.messengers.telegram.interface import PollingTelegramInterface
from dff.messengers.telegram.message import TelegramMessage, TelegramUI, RemoveKeyboard, _ClickButton


def replace_click_button(happy_path):
    """
    Replace all _ClickButton instances in `happy_path`.
    This allows using :py:func:`~dff.utils.testing.common.check_happy_path` instead of
    :py:meth:~dff.utils.testing.telegram.TelegramTesting.check_happy_path`.

    :return: A `happy_path` with all `_ClickButton` replaced with payload values of the buttons.
    """
    result = deepcopy(happy_path)
    for index in range(len(happy_path)):
        user_request = happy_path[index][0]
        if not isinstance(user_request, TelegramMessage):
            continue
        if isinstance(user_request.callback_query, _ClickButton):
            callback_query = None
            for _, bot_response in reversed(happy_path[:index]):
                if isinstance(bot_response, TelegramMessage) and bot_response.ui is not None and callback_query is None:
                    callback_query = bot_response.ui.buttons[user_request.callback_query.button_index].payload
            if callback_query is None:
                raise RuntimeError("Bot response with buttons not found.")
            result[index][0].callback_query = callback_query
    return result


async def get_bot_user(client: TelegramClient, username: str):
    async with client:
        return await client.get_entity(username)


class TelegramTesting:  # pragma: no cover
    """
    Defines functions for testing.

    :param pipeline:
        Pipeline with the telegram messenger interface.
        Required for :py:meth:`~dff.utils.testing.telegram.TelegramTesting.send_and_check` and
        :py:meth:`~dff.utils.testing.telegram.TelegramTesting.check_happy_path` with `run_bot=True`
    :param api_credentials:
        Telegram API id and hash.
        Obtainable via https://core.telegram.org/api/obtaining_api_id.
    :param session_file:
        A `telethon` session file.
        Obtainable by connecting to :py:class:`telethon.TelegramClient` and entering phone number and code.
    :param client:
        An alternative to passing `api_credentials` and `session_file`.
    :param bot_username:
        Either a link to the bot user or its handle. Used to determine whom to talk with as a client.
    :param bot:
        An alternative to passing `bot_username`.
        Result of calling :py:func:`~dff.utils.testing.telegram.get_bot_user` with `bot_username` as parameter.
    """

    def __init__(
        self,
        pipeline: Pipeline,
        api_credentials: Optional[Tuple[int, str]] = None,
        session_file: Optional[str] = None,
        client: Optional[TelegramClient] = None,
        bot_username: Optional[str] = None,
        bot: Optional[User] = None,
    ):
        if client is None:
            if api_credentials is None or session_file is None:
                raise RuntimeError("Pass either `client` or `api_credentials` and `session_file`.")
            client = TelegramClient(session_file, *api_credentials)
        self.client = client
        """Telegram client (not bot). Needed to verify bot replies."""
        self.pipeline = pipeline
        if bot is None:
            if bot_username is None:
                raise RuntimeError("Pass either `bot_username` or `bot`.")
            bot = asyncio.run(get_bot_user(self.client, bot_username))
        self.bot = bot
        """Bot user (to know whom to send messages to from client)."""

    async def send_message(self, message: TelegramMessage, last_bot_messages: List[TlMessage]):
        """
        Send a message from client to bot.
        If the message contains `callback_query`, only press the button, ignore other fields.

        :param message: Message to send.
        :param last_bot_messages:
            The last bot response. Accepts a list because messages with multiple fields are split in telegram.
            Can only contain one keyboard in the list.
            Used to determine which button to press when message contains
            :py:class:`~dff.messengers.telegram.message._ClickButton`.
        """
        if message.callback_query is not None:
            query = message.callback_query
            if not isinstance(query, _ClickButton):
                raise RuntimeError(f"Use `_ClickButton` during tests: {query}")
            for bot_message in last_bot_messages:
                if bot_message.buttons is not None:
                    await bot_message.click(i=query.button_index)
                    return None
        if message.attachments is None or len(message.attachments.files) == 0:
            return await self.client.send_message(self.bot, message.text)
        else:
            if len(message.attachments.files) == 1:
                attachment = message.attachments.files[0]
                files = attachment.source
            else:
                files = [file.source for file in message.attachments.files]
            return await self.client.send_file(self.bot, files, caption=message.text)

    @staticmethod
    async def parse_responses(responses: List[TlMessage], file_download_destination) -> Message:
        """
        Convert a list of bot responses into a single message.
        This function accepts a list because messages with multiple attachments are split.

        :param responses: A list of bot responses that are considered to be a single message.
        :param file_download_destination: A directory to download sent media to.
        """
        msg = TelegramMessage()
        for response in responses:
            if response.text and response.file is None:
                if msg.text:
                    raise RuntimeError(f"Several messages with text:\n{msg.text}\n{response.text}")
                msg.text = response.text or msg.text
            if response.file is not None:
                file = Path(file_download_destination) / (str(response.file.media.id) + response.file.ext)
                await response.download_media(file=file)
                if msg.attachments is None:
                    msg.attachments = Attachments()
                msg.attachments.files.append(
                    Attachment(source=file, id=None, title=response.file.title or response.text or None)
                )
            if response.buttons is not None:
                buttons = []
                for row in response.buttons:
                    for button in row:
                        buttons.append(
                            Button(
                                source=button.url,
                                text=button.text,
                                payload=button.data,
                            )
                        )
                if msg.ui is not None:
                    raise RuntimeError(f"Several messages with ui:\n{msg.ui}\n{TelegramUI(buttons=buttons)}")
                msg.ui = TelegramUI(buttons=buttons)
            if isinstance(response.reply_markup, ReplyKeyboardHide):
                if msg.ui is not None:
                    raise RuntimeError(f"Several messages with ui:\n{msg.ui}\n{types.ReplyKeyboardRemove()}")
                msg.ui = RemoveKeyboard()
            if response.geo is not None:
                location = Location(latitude=response.geo.lat, longitude=response.geo.long)
                if msg.location is not None:
                    raise RuntimeError(f"Several messages with location:\n{msg.location}\n{location}")
                msg.location = location
        return msg

    @asynccontextmanager
    async def run_bot_loop(self):
        """A context manager that returns a function to run one polling loop of a messenger interface."""
        self.pipeline.messenger_interface.timeout = 2
        self.pipeline.messenger_interface.long_polling_timeout = 2
        await self.forget_previous_updates()

        yield lambda: self.pipeline.messenger_interface._polling_loop(self.pipeline._run_pipeline)

        self.pipeline.messenger_interface.forget_processed_updates()

    async def send_and_check(self, message: Message, file_download_destination=None):
        """
        Send a message from a bot, receive it as client, verify it.

        :param message: Message to send and check.
        :param file_download_destination:
            Temporary directory (used to download sent files).
            Defaults to :py:class:`tempfile.TemporaryDirectory`.
        """
        await self.forget_previous_updates()

        async with self.client:
            messenger_interface = cast(PollingTelegramInterface, self.pipeline.messenger_interface)

            messages = await self.client.get_messages(self.bot, limit=1)
            if len(messages) == 0:
                last_message_id = 0
            else:
                last_message_id = messages[0].id

            messenger_interface.messenger.send_response((await self.client.get_me(input_peer=True)).user_id, message)

            await asyncio.sleep(3)
            bot_messages = [
                x async for x in self.client.iter_messages(self.bot, min_id=last_message_id, from_user=self.bot)
            ]  # iter_messages is used instead of get_messages because get_messages requires bot min_id and max_id

            if file_download_destination is None:
                fd_context = TemporaryDirectory()
            else:
                fd_context = nullcontext(file_download_destination)

            with fd_context as file_download_destination:
                result = await self.parse_responses(bot_messages, file_download_destination)

                assert result == message

    async def forget_previous_updates(self):
        messenger_interface = cast(PollingTelegramInterface, self.pipeline.messenger_interface)
        messenger = messenger_interface.messenger
        updates = messenger.get_updates(offset=messenger.last_update_id + 1, timeout=1, long_polling_timeout=1)
        max_update_id = max([*map(lambda x: x.update_id, updates), -1])
        messenger.get_updates(offset=max_update_id + 1, timeout=1, long_polling_timeout=1)

    async def check_happy_path(self, happy_path, file_download_destination=None, run_bot: bool = True):
        """
        Play out a dialogue with the bot. Check that the dialogue is correct.

        :param happy_path: Expected dialogue
        :param file_download_destination: Temporary directory (used to download sent files)
        :param run_bot: Whether a bot inside pipeline should be running (disable this to test non-async bots)
        :return:
        """
        if run_bot:
            bot = self.run_bot_loop()
        else:

            async def null():
                ...

            bot = nullcontext(null)

        if file_download_destination is None:
            fd_context = TemporaryDirectory()
        else:
            fd_context = nullcontext(file_download_destination)

        async with self.client, bot as boot_loop:
            with fd_context as file_download_destination:
                bot_messages = []
                last_message = None
                for request, response in happy_path:
                    logging.info(f"Sending request {request}")
                    user_message = await self.send_message(TelegramMessage.model_validate(request), bot_messages)
                    if user_message is not None:
                        last_message = user_message
                    logging.info("Request sent")
                    await boot_loop()
                    await asyncio.sleep(2)
                    logging.info("Extracting responses")
                    bot_messages = [
                        x async for x in self.client.iter_messages(self.bot, min_id=last_message.id, from_user=self.bot)
                    ]
                    # iter_messages is used instead of get_messages because get_messages requires bot min_id and max_id
                    if len(bot_messages) > 0:
                        last_message = bot_messages[0]
                    logging.info("Got responses")
                    result = await self.parse_responses(bot_messages, file_download_destination)
                    assert result == TelegramMessage.model_validate(response)
