"""
Dialog Flow Generics
--------------------

This module contains a universal response model that should be supported in all `dff` add-ons.
It only contains types and properties that are compatible with most messaging services.
On the other hand, it can support service-specific ui models.
"""
from typing import Any, Optional, List, Union
from enum import Enum, auto
from pathlib import Path
from urllib.request import urlopen

from pydantic import Extra, Field, ValidationError, FilePath, HttpUrl, BaseModel
from pydantic import validator, root_validator


class Session(Enum):
    ACTIVE = auto()
    FINISHED = auto()


class DataModel(BaseModel):
    class Config:
        extra = Extra.allow
        arbitrary_types_allowed = True


class Command(DataModel):
    ...


class Location(DataModel):
    longitude: float
    latitude: float

    def __eq__(self, other):
        if isinstance(other, Location):
            return abs(self.latitude - other.latitude) + abs(self.longitude - other.longitude) < 0.002
        return NotImplemented


class Attachment(DataModel):
    source: Optional[Union[HttpUrl, FilePath]] = None
    id: Optional[str] = None  # id field is made separate to simplify type validation
    title: Optional[str] = None

    def get_bytes(self) -> Optional[bytes]:
        if self.source is None:
            return None
        if isinstance(self.source, HttpUrl):
            with urlopen(self.source) as file:
                return file.read()
        else:
            with open(self.source, "rb") as file:
                return file.read()

    def __eq__(self, other):
        if isinstance(other, Attachment):
            if self.title != other.title:
                return False
            if self.id != other.id:
                return False
            return self.get_bytes() == other.get_bytes()
        return NotImplemented

    @root_validator
    def validate_source_or_id(cls, values):
        if bool(values.get("source")) == bool(values.get("id")):
            raise ValidationError("Attachment type requires exactly one parameter, `source` or `id`, to be set.")
        return values

    @validator("source")
    def validate_source(cls, value):
        if isinstance(value, Path):
            return Path(value)
        return value


class Audio(Attachment):
    pass


class Video(Attachment):
    pass


class Image(Attachment):
    pass


class Document(Attachment):
    pass


class Attachments(DataModel):
    files: List[Attachment] = Field(default_factory=list)

    def __eq__(self, other):
        if isinstance(other, Attachments):
            return self.files == other.files
        return NotImplemented


class Link(DataModel):
    source: HttpUrl
    title: Optional[str] = None

    @property
    def html(self):
        return f'<a href="{self.source}">{self.title if self.title else self.source}</a>'


class Button(DataModel):
    source: Optional[HttpUrl] = None
    text: str
    payload: Optional[Any] = None

    def __eq__(self, other):
        if isinstance(other, Button):
            if self.source != other.source:
                return False
            if self.text != other.text:
                return False
            first_payload = bytes(self.payload, encoding="utf-8") if isinstance(self.payload, str) else self.payload
            second_payload = bytes(other.payload, encoding="utf-8") if isinstance(other.payload, str) else other.payload
            return first_payload == second_payload
        return NotImplemented


class Keyboard(DataModel):
    buttons: List[Button] = Field(default_factory=list, min_items=1)

    def __eq__(self, other):
        if isinstance(other, Keyboard):
            return self.buttons == other.buttons
        return NotImplemented


class Message(DataModel):
    text: Optional[str] = None
    commands: Optional[List[Command]] = None
    attachments: Optional[Attachments] = None
    annotations: Optional[dict] = None
    misc: Optional[dict] = None
    # commands and state options are required for integration with services
    # that use an intermediate backend server, like Yandex's Alice
    # state: Optional[Session] = Session.ACTIVE
    # ui: Optional[Union[Keyboard, DataModel]] = None

    def __eq__(self, other):
        if isinstance(other, Message):
            for field in self.__fields__:
                if field not in other.__fields__:
                    return False
                if self.__getattribute__(field) != other.__getattribute__(field):
                    return False
            return True
        return NotImplemented

    def __repr__(self) -> str:
        return " ".join([f"{key}='{value}'" for key, value in self.dict(exclude_none=True).items()])


class MultiMessage(Message):
    messages: Optional[List[Message]] = None
