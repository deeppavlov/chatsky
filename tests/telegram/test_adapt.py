import pytest
import sys
import json

from telebot import types

sys.path.insert(0, "../dff-generics")

from dff.connectors.messenger.telegram.types import TelegramResponse, TelegramAttachments, TelegramAttachment
from dff.connectors.messenger.generics import Attachments, Response, Keyboard, Button, Image


def test_adapt_buttons():
    generic_response = Response(
        text="test",
        ui=Keyboard(
            buttons=[
                Button(text="button 1", payload=json.dumps({"text": "1", "other_prop": "4"})),
                Button(text="button 2", payload=json.dumps({"text": "2", "other_prop": "3"})),
                Button(text="button 3", payload=json.dumps({"text": "3", "other_prop": "2"})),
                Button(text="button 4", payload=json.dumps({"text": "4", "other_prop": "1"})),
            ]
        ),
    )
    telegram_response = TelegramResponse.parse_obj(generic_response)
    assert telegram_response.text == generic_response.text
    assert telegram_response.ui and isinstance(telegram_response.ui.keyboard, types.InlineKeyboardMarkup)
    print(telegram_response.ui.keyboard.keyboard)
    assert len(telegram_response.ui.keyboard.keyboard) == 2
    assert isinstance(telegram_response.ui.keyboard.keyboard[0][0], types.InlineKeyboardButton)


def test_telegram_attachment():
    generic_response = Response(text="test", image=Image(source="https://folklore.linghub.ru/api/gallery/300/23.JPG"))
    telegram_response = TelegramResponse.parse_obj(generic_response)
    assert telegram_response.image and isinstance(telegram_response.image, TelegramAttachment)
    assert telegram_response.image.source == generic_response.image.source


def test_adapt_attachments():
    generic_response = Response(
        text="test",
        attachments=Attachments(
            files=[
                Image(source="https://folklore.linghub.ru/api/gallery/300/23.JPG", title="image 1"),
                Image(source="https://folklore.linghub.ru/api/gallery/300/22.JPG", title="image 2"),
            ]
        ),
    )
    telegram_response = TelegramResponse.parse_obj(generic_response)
    assert telegram_response.text == generic_response.text
    assert telegram_response.attachments and isinstance(telegram_response.attachments, TelegramAttachments)
    assert len(telegram_response.attachments.files) == 2
    assert isinstance(telegram_response.attachments.files[0], types.InputMediaPhoto)
    assert telegram_response.attachments.files[0].media == generic_response.attachments.files[0].source
    assert telegram_response.attachments.files[0].caption == generic_response.attachments.files[0].title
