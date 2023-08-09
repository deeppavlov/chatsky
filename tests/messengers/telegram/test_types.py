import json
from io import IOBase
from pathlib import Path

import pytest

try:
    import telebot  # noqa: F401
    import telethon  # noqa: F401
except ImportError:
    pytest.skip(reason="`telegram` is not available", allow_module_level=True)

from pydantic import ValidationError
from telebot import types

from dff.messengers.telegram.message import (
    TelegramMessage,
    TelegramUI,
    RemoveKeyboard,
    ParseMode,
)
from dff.script import Message
from dff.script.core.message import Attachments, Keyboard, Button, Image, Location, Audio, Video, Attachment, Document
from dff.messengers.telegram.utils import open_io, close_io, batch_open_io

from dff.utils.testing.telegram import TelegramTesting

image = Image(
    source="https://gist.githubusercontent.com/scotthaleen/32f76a413e0dfd4b4d79c2a534d49c0b/raw"
    "/6c1036b1eca90b341caf06d4056d36f64fc11e88/tiny.jpg"
)
audio = Audio(source="https://github.com/mathiasbynens/small/raw/master/mp3.mp3")
video = Video(source="https://github.com/mathiasbynens/small/raw/master/Mpeg4.mp4")
document = Document(source="https://github.com/mathiasbynens/small/raw/master/pdf.pdf")


@pytest.mark.asyncio
@pytest.mark.telegram
async def test_text(pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = TelegramMessage(text="test")
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


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
@pytest.mark.telegram
async def test_buttons(ui, button_type, markup_type, pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = TelegramMessage(text="test", ui=ui)
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


@pytest.mark.asyncio
@pytest.mark.telegram
async def test_keyboard_remove(pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = TelegramMessage(text="test", ui=RemoveKeyboard())
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["generic_response"],
    [
        (
            Message(
                text="test",
                attachments=Attachments(files=[image]),
            ),
        ),
        (
            Message(
                text="test",
                attachments=Attachments(files=[audio]),
            ),
        ),
        (
            Message(
                text="test",
                attachments=Attachments(files=[video]),
            ),
        ),
        (Message(text="test", attachments=Attachments(files=[document])),),
    ],
)
@pytest.mark.telegram
async def test_telegram_attachment(generic_response, pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = TelegramMessage.model_validate(generic_response)
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["attachments"],
    [
        (
            Message(
                text="test",
                attachments=Attachments(files=2 * [image]),
            ),
        ),
        (
            Message(
                text="test",
                attachments=Attachments(files=2 * [audio]),
            ),
        ),
        (
            Message(
                text="test",
                attachments=Attachments(files=2 * [video]),
            ),
        ),
        (Message(text="test", attachments=Attachments(files=2 * [document])),),
    ],
)
@pytest.mark.telegram
async def test_attachments(attachments, pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = TelegramMessage.model_validate(attachments)
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


@pytest.mark.asyncio
@pytest.mark.telegram
async def test_location(pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = TelegramMessage(text="location", location=Location(longitude=39.0, latitude=43.0))
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


@pytest.mark.asyncio
@pytest.mark.telegram
async def test_parsed_text(pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = TelegramMessage(text="[inline URL](http://www.example.com/)", parse_mode=ParseMode.MARKDOWN)
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


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
