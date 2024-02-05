"""
Interface
------------
This module implements various interfaces for :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger`
that can be used to interact with the Telegram API.
"""
from typing import Callable, Optional, Sequence, cast
from pydantic import HttpUrl
import asyncio

# from vkbottle import API
from vkwave.bots import SimpleLongPollBot, SimpleBotEvent
import requests

from dff.messengers.common import MessengerInterface
from dff.pipeline import Pipeline
# from dff.pipeline.types import PipelineRunnerFunction
from dff.script.core.context import Context
from dff.script.core.message import  Audio, Button, Document, Image, Keyboard, Location, Message, Video


def _create_keyboard(buttons: Sequence[Sequence[Button]]):
    pass

class _AbstractVKInterface(MessengerInterface):
    def __init__(self, token: str, group_id: str) -> None:
        self.bot = SimpleLongPollBot(tokens=token, group_id=group_id)
        self.bot.message_handler()(self.on_message)
    
    
    def extract_message_from_vk(self, message_vk) -> Message:
        message = Message()
        message.attachments = list()

        if message_vk.object.object.message.text is not None:
            message.text = message_vk.object.object.message.text
        
        if message_vk.attachments is not []:
            for element in message_vk["attachments"]:
                match element["type"]:
                    case "photo":
                        message.attachments += [Image(source=HttpUrl(element[element["type"]]['sizes'][-1]['url']))]
                    case "video":
                        pass
                    case "audio":
                        pass
                    case "doc":
                        pass
                    case "link":
                        pass
                    case _:
                        pass

        return message


    async def cast_message_to_vk_and_send(self, bot: SimpleLongPollBot, orig_message, message: Message) -> None:
        if message.attachments is not None:
            pass
        if message.text is not None:
            await orig_message.answer(message=message.text)


    async def on_message(self, event: SimpleBotEvent) -> None:
        message = await self.extract_message_from_vk(event)
        message.original_message = event
        resp = await self.callback(message, event.object.object.message.peer_id)
        if resp.last_response is not None:
            await self.cast_message_to_vk_and_send(self.bot, event, resp.last_response)


    async def connect(self, callback, *args, **kwargs):
        self.callback = callback

class PollingVKInterface(_AbstractVKInterface):
    def __init__(self, token: str) -> None:
        super().__init__(token)

    async def connect(self, callback, *args, **kwargs):
        await super().connect(callback, *args, **kwargs)
        self.bot.run_forever()
