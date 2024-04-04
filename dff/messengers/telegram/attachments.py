from typing import Optional

from dff.script.core.message import Animation, Audio, Contact, Document, Image, Poll, Video


class TelegramContact(Contact):
    user_id: Optional[int]


class TelegramPoll(Poll):
    is_closed: bool
    is_anonymous: bool
    type: str
    multiple_answers: bool
    correct_option_id: Optional[int]
    explanation: Optional[str]
    open_period: Optional[int]


class TelegramAudio(Audio):
    duration: int
    performer: Optional[str]
    file_name: Optional[str]
    mime_type: Optional[str]
    thumbnail: Optional[Image]


class TelegramVideo(Video):
    width: int
    height: int
    duration: int
    file_name: Optional[str]
    mime_type: Optional[str]
    thumbnail: Optional[Image]


class TelegramAnimation(Animation):
    width: int
    height: int
    duration: int
    file_name: Optional[str]
    mime_type: Optional[str]
    thumbnail: Optional[Image]


class TelegramImage(Image):
    width: int
    height: int


class TelegramDocument(Document):
    file_name: Optional[str]
    mime_type: Optional[str]
    thumbnail: Optional[Image]
