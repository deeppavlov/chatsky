from os import urandom
from pathlib import Path
from random import randint
from shutil import rmtree
from typing import Hashable, Optional, TextIO
from urllib.request import urlopen

import pytest
from pydantic import ValidationError, HttpUrl, FilePath

from chatsky.messengers.common.interface import MessengerInterfaceWithAttachments
from chatsky.messengers.console import CLIMessengerInterface
from chatsky.script.core.message import (
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

EXAMPLE_SOURCE = "https://github.com/deeppavlov/chatsky/wiki/example_attachments"


class UnserializableObject:
    def __init__(self, number: int, string: bytes) -> None:
        self.number = number
        self.bytes = string

    def __eq__(self, value: object) -> bool:
        if isinstance(value, UnserializableObject):
            return self.number == value.number and self.bytes == value.bytes
        else:
            return False


class ChatskyCLIMessengerInterface(CLIMessengerInterface, MessengerInterfaceWithAttachments):
    supported_response_attachment_types = {Document}

    def __init__(self, attachments_directory: Optional[Path] = None):
        MessengerInterfaceWithAttachments.__init__(self, attachments_directory)
        self._ctx_id: Optional[Hashable] = None
        self._intro: Optional[str] = None
        self._prompt_request: str = "request: "
        self._prompt_response: str = "response: "
        self._descriptor: Optional[TextIO] = None

    async def get_attachment_bytes(self, attachment: str) -> bytes:
        with urlopen(f"{EXAMPLE_SOURCE}/{attachment}") as url:
            return url.read()


class TestMessage:
    @pytest.fixture
    def random_original_message(self) -> UnserializableObject:
        return UnserializableObject(randint(0, 256), urandom(32))

    def clear_and_create_dir(self, dir: Path) -> Path:
        rmtree(dir, ignore_errors=True)
        dir.mkdir()
        return dir

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
        cli_iface = ChatskyCLIMessengerInterface(self.clear_and_create_dir(tmp_path / "cache"))

        document_name = "deeppavlov-article.pdf"
        remote_document_url = f"{EXAMPLE_SOURCE}/{document_name}"
        with urlopen(remote_document_url) as url:
            document_bytes = url.read()
            local_document.write_bytes(document_bytes)

        remote_document_att = Document(source=str(remote_document_url))
        local_document_att = Document(source=str(local_document))
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
