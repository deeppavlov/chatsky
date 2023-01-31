from typing import List
from contextlib import asynccontextmanager
import logging
import asyncio

import telethon.tl.types
from telethon import TelegramClient
from telethon.types import User
from telethon.custom import Message as TlMessage
from telebot import types

from dff.pipeline.pipeline.pipeline import Pipeline
from dff.script.core.message import Message, Attachments, Attachment, Button, Location
from dff.messengers.telegram.interface import PollingTelegramInterface
from dff.messengers.telegram.message import TelegramMessage, TelegramUI, RemoveKeyboard, _ClickButton


class TelegramTesting:
    """Defines functions for testing."""

    def __init__(self, client: TelegramClient, pipeline: Pipeline, bot: User):
        self.client = client
        """Telegram client (not bot). Needed to verify bot replies."""
        self.pipeline = pipeline
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
        """A context manager that start a bot"""
        self.pipeline.messenger_interface.timeout = 2
        self.pipeline.messenger_interface.long_polling_timeout = 2
        task = asyncio.create_task(self.pipeline.messenger_interface.connect(self.pipeline._run_pipeline))
        logging.info("Bot created")
        yield
        self.pipeline.messenger_interface.stop()
        await task

    async def send_and_check(self, message: Message, tmp_dir):
        """Send a message from a bot, receive it as client, verify it."""
        messenger_interface = self.pipeline.messenger_interface
        assert isinstance(messenger_interface, PollingTelegramInterface)

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

    async def check_happy_path(self, happy_path, tmp_dir):
        async with self.run_bot():
            bot_messages = []
            last_message = None
            for request, response in happy_path:
                logging.info("Sending request")
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
            self.pipeline.messenger_interface.stop()
