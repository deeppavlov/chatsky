import json
from io import IOBase
from pathlib import Path

import pytest

try:
    import telegram  # noqa: F401
except ImportError:
    pytest.skip(reason="`telegram` is not available", allow_module_level=True)

from pydantic import FilePath, HttpUrl, ValidationError

from dff.script import Message
from dff.script.core.message import Button, DataAttachment, Keyboard, Image, Location, Audio, Video, Attachment, Document

from dff.utils.testing.telegram import TelegramTesting

_image_link = "https://gist.githubusercontent.com/scotthaleen/32f76a413e0dfd4b4d79c2a534d49c0b/raw/6c1036b1eca90b341caf06d4056d36f64fc11e88/tiny.jpg"
image = Image(source=HttpUrl(_image_link))
audio = Audio(source=HttpUrl("https://github.com/mathiasbynens/small/raw/master/mp3.mp3"))
video = Video(source=HttpUrl("https://github.com/mathiasbynens/small/raw/master/Mpeg4.mp4"))
document = Document(source=HttpUrl("https://github.com/mathiasbynens/small/raw/master/pdf.pdf"))


@pytest.mark.asyncio
@pytest.mark.telegram
async def test_text(pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = Message(text="test")
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["keyboard"],
    [
        Keyboard(
            buttons=[
                [
                    Button(text="button 1", data=json.dumps({"text": "1", "other_prop": "4"})),
                    Button(text="button 2", data=json.dumps({"text": "2", "other_prop": "3"})),
                ],
                [
                    Button(text="button 3", data=json.dumps({"text": "3", "other_prop": "2"})),
                    Button(text="button 4", data=json.dumps({"text": "4", "other_prop": "1"})),
                ]
            ]
        ),
        Keyboard(
            buttons=[
                [
                    Button(text="button 1"),
                    Button(text="button 2"),
                ],
                [
                    Button(text="button 3"),
                    Button(text="button 4"),
                ]
            ],
        ),
    ],
)
@pytest.mark.telegram
async def test_buttons(keyboard: Keyboard, pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = Message(text="test", attachments=[keyboard])
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
                attachments=[image],
            ),
        ),
        (
            Message(
                text="test",
                attachments=[audio],
            ),
        ),
        (
            Message(
                text="test",
                attachments=[video],
            ),
        ),
        (
            Message(
                text="test",
                attachments=[document],
            ),
        ),
    ],
)
@pytest.mark.telegram
async def test_telegram_attachment(generic_response, pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = Message.model_validate(generic_response)
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
                attachments=list(tuple(2 * [image])),
            ),
        ),
        (
            Message(
                text="test",
                attachments=list(tuple(2 * [audio])),
            ),
        ),
        (
            Message(
                text="test",
                attachments=list(tuple(2 * [video])),
            ),
        ),
        (
            Message(
                text="test",
                attachments=list(tuple(2 * [document])),
            ),
        ),
    ],
)
@pytest.mark.telegram
async def test_attachments(attachments, pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = Message.model_validate(attachments)
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


@pytest.mark.asyncio
@pytest.mark.telegram
async def test_location(pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = Message(text="location", attachments=[Location(longitude=39.0, latitude=43.0)])
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


@pytest.mark.asyncio
@pytest.mark.telegram
async def test_parsed_text(pipeline_instance, api_credentials, bot_user, session_file):
    telegram_response = Message(text="[inline URL](http://www.example.com/)", parse_mode=ParseMode.MARKDOWN)
    test_helper = TelegramTesting(
        pipeline=pipeline_instance, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    await test_helper.send_and_check(telegram_response)


def test_missing_error():
    with pytest.raises(ValidationError) as e:
        _ = DataAttachment(source=HttpUrl("http://google.com"), id="123")
    assert e

    with pytest.raises(ValidationError) as e:
        _ = DataAttachment(source=FilePath("/etc/missing_file"))
    assert e


def test_empty_keyboard():
    with pytest.raises(ValidationError) as e:
        _ = Keyboard(buttons=[])
    assert e


def test_long_button_data():
    with pytest.raises(ValidationError) as error:
        Button(text="", data="test" * 64)
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
