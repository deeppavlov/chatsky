"""
Interface
------------
This module implements various interfaces for :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger`
that can be used to interact with the Telegram API.
"""
from typing import Callable, Optional, Sequence, cast
from pydantic import HttpUrl

from pyvkbot import Bot
import requests

from dff.messengers.common import MessengerInterface
from dff.pipeline import Pipeline
from dff.pipeline.types import PipelineRunnerFunction
from dff.script.core.context import Context
from dff.script.core.message import Animation, Audio, Button, Contact, Document, Image, Invoice, Keyboard, Location, Message, Poll, PollOption, Video


def extract_message_from_vk(message_vk: dict[str, str]) -> Message:
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
                    pass
                case "doc":
                    pass
                case "link":
                    pass
                case _:
                    pass

    return message

def _create_keyboard(buttons: Sequence[Sequence[Button]]):
    pass


async def cast_message_to_vk_and_send(bot: Bot, chat_id: int, message: Message) -> None:
    pass


class _AbstractVKInterface(MessengerInterface):
    def __init__(self, token: str, group_id: str) -> None:
        self.bot = Bot(token=token, group_id=group_id)
        self.bot.on('message', self.on_message)

    async def on_message(self, bot: Bot, message: dict[str, str]) -> None:
        pass


class PollingVKInterface(_AbstractVKInterface):
    pass


if __name__=="__main__":
    KEY = "<YOUR_KEY>"
    GROUP_ID = "<YOUR_GROUP_ID>"

    bot = Bot(token=KEY, group_id=GROUP_ID)

    def echo(bot: Bot, message: dict[str, str]):
        for element in message["attachments"]:
            print(element[element["type"]])
        bot.send_message(peer_id=message["peer_id"], text="thx")

    bot.on('message', echo)

    bot.start_polling(lambda: print("Bot started"))