from os import urandom
from pathlib import Path
from random import randint
from shutil import rmtree
from typing import Hashable, Optional, TextIO
from urllib.request import urlopen

import pytest
from pydantic import ValidationError, HttpUrl, FilePath

from dff.messengers.common.interface import MessengerInterface
from dff.messengers.console import CLIMessengerInterface
from dff.script.core.message import (
    Animation,
    Audio,
    CallbackQuery,
    Contact,
    Document,
    Image,
    Invoice,
    Location,
    DataAttachment,
    Message,
    Poll,
    PollOption,
    Sticker,
    Video,
)

EXAMPLE_SOURCE = "https://github.com/deeppavlov/dialog_flow_framework/wiki/example_attachments"


class UnserializableObject:
    def __init__(self, number: int, string: bytes) -> None:
        self.number = number
        self.bytes = string

    def __eq__(self, value: object) -> bool:
        if isinstance(value, UnserializableObject):
            return self.number == value.number and self.bytes == value.bytes
        else:
            return False


class DFFCLIMessengerInterface(CLIMessengerInterface):
    def __init__(self, attachments_directory: Optional[Path] = None):
        MessengerInterface.__init__(self, attachments_directory)
        self._ctx_id: Optional[Hashable] = None
        self._intro: Optional[str] = None
        self._prompt_request: str = "request: "
        self._prompt_response: str = "response: "
        self._descriptor: Optional[TextIO] = None

    async def populate_attachment(self, attachment: DataAttachment) -> bytes:
        if attachment.id is not None:
            with urlopen(f"{EXAMPLE_SOURCE}/{attachment.id}") as url:
                return url.read()
        else:
            raise ValueError(f"For attachment {attachment} id is not defined!")


class TestMessage:
    @pytest.fixture
    def random_original_message(self) -> UnserializableObject:
        return UnserializableObject(randint(0, 256), urandom(32))

    def clear_and_create_dir(self, dir: Path) -> Path:
        rmtree(dir, ignore_errors=True)
        dir.mkdir()
        return dir

    def test_location(self):
        loc1 = Location(longitude=-0.1, latitude=-0.1)
        loc2 = Location(longitude=-0.09999, latitude=-0.09998)
        loc3 = Location(longitude=-0.10002, latitude=-0.10001)

        assert loc1 == loc2
        assert loc3 == loc1
        assert loc2 != loc3

        assert loc1 != 1

    @pytest.mark.parametrize(
        "attachment1,attachment2,equal",
        [
            (
                DataAttachment(source="https://github.com/mathiasbynens/small/raw/master/pdf.pdf", title="Title"),
                DataAttachment(source="https://github.com/mathiasbynens/small/raw/master/pdf.pdf", title="Title"),
                True,
            ),
            (
                DataAttachment(source="https://github.com/mathiasbynens/small/raw/master/pdf.pdf", title="File"),
                DataAttachment(
                    source="https://raw.githubusercontent.com/mathiasbynens/small/master/pdf.pdf", title="File"
                ),
                False,
            ),
            (
                DataAttachment(source="https://github.com/mathiasbynens/small/raw/master/pdf.pdf", title="1"),
                DataAttachment(source="https://github.com/mathiasbynens/small/raw/master/pdf.pdf", title="2"),
                False,
            ),
            (
                DataAttachment(source=__file__, title="File"),
                DataAttachment(source=__file__, title="File"),
                True,
            ),
            (
                DataAttachment(source=__file__, title="1"),
                DataAttachment(source=__file__, title="2"),
                False,
            ),
            (
                DataAttachment(id="1", title="File"),
                DataAttachment(id="2", title="File"),
                False,
            ),
        ],
    )
    def test_attachment_equal(self, attachment1: DataAttachment, attachment2: DataAttachment, equal: bool):
        assert (attachment1 == attachment2) == equal

    @pytest.mark.parametrize(
        "attachment",
        [
            CallbackQuery(query_string="some_callback_query_data"),
            Location(longitude=53.055955, latitude=102.891407),
            Contact(phone_number="8-900-555-35-35", first_name="Hope", last_name="Credit"),
            Invoice(title="Payment", description="No comment", currency="USD", amount=300),
            Poll(question="Which?", options=[PollOption(text="1", votes=2), PollOption(text="2", votes=5)]),
            Audio(source="https://example.com/some_audio.mp3"),
            Video(source="https://example.com/some_video.mp4"),
            Animation(source="https://example.com/some_animation.gif"),
            Image(source="https://example.com/some_image.png"),
            Sticker(id="some_sticker_identifier"),
            Document(source="https://example.com/some_document.pdf"),
        ],
    )
    def test_attachment_serialize(self, attachment: DataAttachment):
        message = Message(attachments=[attachment])
        serialized = message.model_dump_json()
        validated = Message.model_validate_json(serialized)
        assert message == validated

    def test_field_serializable(self, random_original_message: UnserializableObject):
        message = Message(text="sample message")
        message.misc = {"answer": 42, "unserializable": random_original_message}
        message.original_message = random_original_message
        message.some_extra_field = random_original_message
        message.other_extra_field = {"unserializable": random_original_message}
        serialized = message.model_dump_json()
        validated = Message.model_validate_json(serialized)
        assert message == validated

    @pytest.mark.asyncio
    async def test_getting_attachment_bytes(self, tmp_path):
        local_path = self.clear_and_create_dir(tmp_path / "local")

        local_document = local_path / "pre-saved-document.pdf"
        cli_iface = DFFCLIMessengerInterface(self.clear_and_create_dir(tmp_path / "cache"))

        document_name = "deeppavlov-article.pdf"
        remote_document_url = f"{EXAMPLE_SOURCE}/{document_name}"
        with urlopen(remote_document_url) as url:
            document_bytes = url.read()
            local_document.write_bytes(document_bytes)

        remote_document_att = Document(source=HttpUrl(remote_document_url))
        local_document_att = Document(source=FilePath(local_document))
        iface_document_att = Document(id=document_name)

        for document in (remote_document_att, local_document_att, iface_document_att):
            read_bytes = await document.get_bytes(cli_iface)
            assert document_bytes == read_bytes
            if not isinstance(document.source, Path):
                assert document.cached_filename is not None
                cached_bytes = document.cached_filename.read_bytes()
                assert document_bytes == cached_bytes

    def test_missing_error(self):
        with pytest.raises(ValidationError) as e:
            _ = DataAttachment(source=HttpUrl("http://google.com"), id="123")
        assert e

        with pytest.raises(ValidationError) as e:
            _ = DataAttachment(source=FilePath("/etc/missing_file"))
        assert e
