from typing import List, Optional, cast
from contextlib import asynccontextmanager
import logging
import asyncio
from os import getenv

import telethon.tl.types
from telethon import TelegramClient
from telethon.types import User
from telethon.custom import Message as TlMessage
from telebot import types

from dff.pipeline.pipeline.pipeline import Pipeline
from dff.script.core.message import Message, Attachments, Attachment, Button, Location
from dff.messengers.telegram.interface import PollingTelegramInterface
from dff.messengers.telegram.message import TelegramMessage, TelegramUI, RemoveKeyboard, _ClickButton


async def get_bot_user(client: TelegramClient, username: str):
    async with client:
        return await client.get_entity(username)


class TelegramTesting:
    """Defines functions for testing."""

    def __init__(self, pipeline: Pipeline, client: Optional[TelegramClient] = None, bot: Optional[User] = None):
        if client is None:
            tg_id = getenv("TG_API_ID")
            tg_hash = getenv("TG_API_HASH")
            if tg_id is not None and tg_hash is not None:
                client = TelegramClient("anon", int(tg_id), tg_hash)
            else:
                raise RuntimeError("Telegram API credentials are not set, client argument is not specified")
        self.client = client
        """Telegram client (not bot). Needed to verify bot replies."""
        self.pipeline = pipeline
        if bot is None:
            bot = getenv("TG_BOT_USERNAME")
            if bot is None:
                raise RuntimeError("Bot username is not set, bot argument is not specified")
            bot = asyncio.run(get_bot_user(self.client, bot))
        self.bot = bot
        """Bot user (to know to whom to send messages from client)."""

    async def send_message(self, message: Message, last_bot_messages: List[TlMessage]):
        """Send a message from client to bot."""
        if message.commands is not None:
            if len(message.commands) != 1:
                raise RuntimeError(f"Multiple commands are not used in telegram: {message.commands}")
            command = message.commands[0]
            if not isinstance(command, _ClickButton):
                raise RuntimeError(f"Only `_ClickButton` command is supported by telegram: {command}")
            button_clicked = False
            for bot_message in last_bot_messages:
                if bot_message.buttons is not None:
                    if button_clicked:
                        raise RuntimeError("Found multiple messages with buttons")
                    await bot_message.click(i=command.button_index)
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
    async def parse_responses(responses: List[TlMessage], tmp_dir) -> Message:
        """
        Convert a list of bot responses into a single message.
        This function accepts a list because messages with multiple attachments are split.
        """
        msg = TelegramMessage()
        for response in responses:
            if response.text is not None and response.file is None:
                if msg.text:
                    raise RuntimeError(f"Several messages with text:\n{msg.text}\n{response.text}")
                msg.text = response.text or msg.text
            if response.file is not None:
                file = tmp_dir / (str(response.file.media.id) + response.file.ext)
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
            if isinstance(response.reply_markup, telethon.tl.types.ReplyKeyboardHide):
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
    async def run_bot(self):
        """A context manager that starts a bot defined in `pipeline`"""
        self.pipeline.messenger_interface.timeout = 2
        self.pipeline.messenger_interface.long_polling_timeout = 2
        task = asyncio.create_task(self.pipeline.messenger_interface.connect(self.pipeline._run_pipeline))
        logging.info("Bot created")
        yield
        self.pipeline.messenger_interface.stop()
        await task

    async def send_and_check(self, message: Message, tmp_dir):
        """Send a message from a bot, receive it as client, verify it."""
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
            ]
            bot_messages.reverse()
            result = await self.parse_responses(bot_messages, tmp_dir)

            assert result == message

    async def forget_previous_updates(self):
        messenger_interface = cast(PollingTelegramInterface, self.pipeline.messenger_interface)
        messenger = messenger_interface.messenger
        updates = messenger.get_updates(offset=messenger.last_update_id + 1, timeout=1, long_polling_timeout=1)
        max_update_id = max([*map(lambda x: x.update_id, updates), -1])
        messenger.get_updates(offset=max_update_id + 1, timeout=1, long_polling_timeout=1)

    async def check_happy_path(self, happy_path, tmp_dir, run_bot: bool = True):
        """
        Play out a dialogue with the bot. Check that the dialogue is correct.

        :param happy_path: Expected dialogue
        :param tmp_dir: Temporary directory (used to download sent files to)
        :param run_bot: Whether a bot inside pipeline should be running (disable this to test non-async bots)
        :return:
        """

        async def _check_happy_path():
            bot_messages = []
            last_message = None
            for request, response in happy_path:
                logging.info(f"Sending request {request}")
                user_message = await self.send_message(TelegramMessage.parse_obj(request), bot_messages)
                if user_message is not None:
                    last_message = user_message
                logging.info("Request sent")
                await asyncio.sleep(3)
                logging.info("Extracting responses")
                bot_messages = [
                    x
                    async for x in self.client.iter_messages(
                        self.bot, min_id=(user_message or last_message).id, from_user=self.bot
                    )
                ]
                if len(bot_messages) > 0:
                    last_message = bot_messages[0]
                logging.info("Got responses")
                result = await self.parse_responses(bot_messages, tmp_dir)
                assert result == TelegramMessage.parse_obj(response)

        async with self.client:
            if run_bot:
                await self.forget_previous_updates()

                async with self.run_bot():
                    await _check_happy_path()
            else:
                await _check_happy_path()
