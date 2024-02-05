"""
Interface
------------
This module implements various interfaces for :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger`
that can be used to interact with the Telegram API.
"""
from typing import Callable, Optional, Sequence, cast
from pydantic import HttpUrl
# import asyncio

from pyvkbot import Bot
import requests

from dff.messengers.common import MessengerInterface
from dff.pipeline import Pipeline
# from dff.pipeline.types import PipelineRunnerFunction
from dff.script.core.context import Context
from dff.script.core.message import  Audio, Button, Document, Image, Keyboard, Location, Message, Video




class _AbstractVKInterface(MessengerInterface):
    def __init__(self, token: str, group_id: str) -> None:
        self.bot = Bot(token=token, group_id=group_id)
        self.bot.on('message', self.on_message)
    
    def _create_keyboard(self, buttons: Sequence[Sequence[Button]]):
        keyboard = Keyboard(inline=False)
        keyboard.add_button(label="123")
    
    def extract_message_from_vk(self, message_vk: dict[str, str]) -> Message:
        message = Message()
        message.attachments = list()

        if message_vk["text"] is not None:
            message.text = message_vk["text"]

        if message_vk["attachments"] is not []:
            for element in message_vk["attachments"]:
                match element["type"]:
                    case "photo":
                        message.attachments += [Image(source=HttpUrl(element[element["type"]]['sizes'][-1]['url']))]
                    case "video":
                        pass
                    case "audio":
                        message.attachments += [Audio(source=HttpUrl(element[element["type"]]['url']))]
                    case "doc":
                        message.attachments += [Document(source=HttpUrl(element[element["type"]]['url']))]
                    case "link":
                        message.text = element[element["type"]]['url']
                    case _:
                        pass

        return message


    def cast_message_to_vk_and_send(self, bot, orig_message, message: Message) -> None:
        if message.attachments is not None:
            pass
        if message.text is not None:
            bot.send_message(peer_id=orig_message["peer_id"], text=message.text)


    def on_message(self, _, event) -> None:
        message = self.extract_message_from_vk(event)
        message.original_message = event
        resp = self.callback(message, event["peer_id"])
        if resp.last_response is not None:
            self.cast_message_to_vk_and_send(self.bot, event, resp.last_response)


    def connect(self, callback, *args, **kwargs):
        self.callback = callback


class PollingVKInterface(_AbstractVKInterface):
    def __init__(self, token: str, group_id: str) -> None:
        super().__init__(token, group_id)

    def connect(self, callback, *args, **kwargs):
        super().connect(callback, *args, **kwargs)
        self.bot.start_polling(lambda: print("Bot started"))
