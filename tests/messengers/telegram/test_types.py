import json
import pytest
import os

from io import IOBase
from pathlib import Path
from pydantic import ValidationError
from telebot import types
from telethon.tl.types import (
    InputMessagesFilterPhotos,
    InputMessagesFilterMusic,
    InputMessagesFilterVideo,
)

from dff.messengers.telegram.message import (
    TelegramMessage,
    TelegramUI,
    RemoveKeyboard,
    ParseMode,
)
from dff.script import Message
from dff.script.core.message import Attachments, Keyboard, Button, Image, Location, Audio, Video, Attachment
from dff.messengers.telegram.utils import open_io, close_io, batch_open_io
from dff.utils.testing import TelegramTesting

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="`TG_BOT_TOKEN` missing")
@pytest.mark.skipif(not TG_API_ID or not TG_API_HASH, reason="TG credentials missing")
@pytest.mark.asyncio
async def test_text(tmp_path, pipeline_instance):
    telegram_response = TelegramMessage(text="test")
    test_helper = TelegramTesting(pipeline_instance)
    await test_helper.send_and_check(telegram_response, tmp_path)


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="`TG_BOT_TOKEN` missing")
@pytest.mark.skipif(not TG_API_ID or not TG_API_HASH, reason="TG credentials missing")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["ui", "markup_type", "button_type"],
    [
        (
            Keyboard(
                buttons=[
                    Button(text="button 1", payload=json.dumps({"text": "1", "other_prop": "4"})),
                    Button(text="button 2", payload=json.dumps({"text": "2", "other_prop": "3"})),
                    Button(text="button 3", payload=json.dumps({"text": "3", "other_prop": "2"})),
                    Button(text="button 4", payload=json.dumps({"text": "4", "other_prop": "1"})),
                ]
            ),
            types.InlineKeyboardMarkup,
            types.InlineKeyboardButton,
        ),
        (
            TelegramUI(
                is_inline=False,
                buttons=[
                    Button(text="button 1"),
                    Button(text="button 2"),
                    Button(text="button 3"),
                    Button(text="button 4"),
                ],
            ),
            types.ReplyKeyboardMarkup,
            types.KeyboardButton,
        ),
    ],
)
async def test_buttons(ui, button_type, markup_type, tmp_path, pipeline_instance):
    telegram_response = TelegramMessage(text="test", ui=ui)
    test_helper = TelegramTesting(pipeline_instance)
    await test_helper.send_and_check(telegram_response, tmp_path)


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="`TG_BOT_TOKEN` missing")
@pytest.mark.skipif(not TG_API_ID or not TG_API_HASH, reason="TG credentials missing")
@pytest.mark.asyncio
async def test_keyboard_remove(tmp_path, pipeline_instance):
    telegram_response = TelegramMessage(text="test", ui=RemoveKeyboard())
    test_helper = TelegramTesting(pipeline_instance)
    await test_helper.send_and_check(telegram_response, tmp_path)


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="`TG_BOT_TOKEN` missing")
@pytest.mark.skipif(not TG_API_ID or not TG_API_HASH, reason="TG credentials missing")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["generic_response", "prop", "filter_type"],
    [
        (
            Message(
                text="test",
                attachments=Attachments(files=[Image(source="https://folklore.linghub.ru/api/gallery/300/23.JPG")]),
            ),
            "image",
            InputMessagesFilterPhotos,
        ),
        (
            Message(
                text="test",
                attachments=Attachments(files=[Audio(source="https://north-folklore.ru/static/sound/IVD_No44.MP3")]),
            ),
            "audio",
            InputMessagesFilterMusic,
        ),
        (
            Message(
                text="test",
                attachments=Attachments(
                    files=[Video(source="https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4")]
                ),
            ),
            "video",
            InputMessagesFilterVideo,
        ),
    ],
)
async def test_telegram_attachment(generic_response, prop, filter_type, tmp_path, pipeline_instance):
    telegram_response = TelegramMessage.parse_obj(generic_response)
    test_helper = TelegramTesting(pipeline_instance)
    await test_helper.send_and_check(telegram_response, tmp_path)


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="`TG_BOT_TOKEN` missing")
@pytest.mark.skipif(not TG_API_ID or not TG_API_HASH, reason="TG credentials missing")
@pytest.mark.asyncio
async def test_attachments(tmp_path, pipeline_instance):
    generic_response = Message(
        text="test",
        attachments=Attachments(
            files=[
                Image(source="https://folklore.linghub.ru/api/gallery/300/23.JPG", title="image 1"),
                Image(source="https://folklore.linghub.ru/api/gallery/300/22.JPG", title="image 2"),
            ]
        ),
    )
    telegram_response = TelegramMessage.parse_obj(generic_response)
    test_helper = TelegramTesting(pipeline_instance)
    await test_helper.send_and_check(telegram_response, tmp_path)


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="`TG_BOT_TOKEN` missing")
@pytest.mark.skipif(not TG_API_ID or not TG_API_HASH, reason="TG credentials missing")
@pytest.mark.asyncio
async def test_location(tmp_path, pipeline_instance):
    telegram_response = TelegramMessage(text="location", location=Location(longitude=39.0, latitude=43.0))
    test_helper = TelegramTesting(pipeline_instance)
    await test_helper.send_and_check(telegram_response, tmp_path)


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="`TG_BOT_TOKEN` missing")
@pytest.mark.skipif(not TG_API_ID or not TG_API_HASH, reason="TG credentials missing")
@pytest.mark.asyncio
async def test_parsed_text(tmp_path, pipeline_instance):
    telegram_response = TelegramMessage(text="[inline URL](http://www.example.com/)", parse_mode=ParseMode.MARKDOWN)
    test_helper = TelegramTesting(pipeline_instance)
    await test_helper.send_and_check(telegram_response, tmp_path)


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="`TG_BOT_TOKEN` missing")
def test_error(basic_bot):
    with pytest.raises(TypeError) as e:
        basic_bot.send_response(0, 1.2)
    assert e


def test_missing_error():
    with pytest.raises(ValidationError) as e:
        _ = Attachment(source="http://google.com", id="123")
    assert e

    with pytest.raises(ValidationError) as e:
        _ = Attachment(source="/etc/missing_file")
    assert e


def test_attachment_error():
    with pytest.raises(ValidationError) as e:
        _ = Attachments(files=["a", "b"])
    assert e


def test_empty_keyboard():
    with pytest.raises(ValidationError) as e:
        _ = TelegramUI(buttons=[])
    assert e


def test_non_inline_keyboard_with_payload():
    with pytest.raises(ValidationError) as error:
        TelegramUI(buttons=[Button(text="", payload="")], is_inline=False)
    assert error


def test_io(document):
    tele_doc = types.InputMediaDocument(media=Path(document))
    opened_doc = open_io(tele_doc)
    print(type(opened_doc.media))
    assert isinstance(opened_doc.media, IOBase)
    close_io(opened_doc)
    assert opened_doc.media.closed
    with batch_open_io(tele_doc) as med:
        assert isinstance(med.media, IOBase)
    assert tele_doc.media.closed
