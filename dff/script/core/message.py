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

from pydantic import Extra, Field, ValidationError, FilePath, HttpUrl, BaseModel
from pydantic import validator, root_validator


class Session(Enum):
    ACTIVE = auto()
    FINISHED = auto()


class DataModel(BaseModel):
    class Config:
        extra = Extra.allow


class Command(DataModel):
    command: str


class Location(DataModel):
    longitude: float
    latitude: float


class Attachment(DataModel):
    source: Optional[Union[HttpUrl, FilePath]] = None
    id: Optional[str] = None  # id field is made separate to simplify type validation
    title: Optional[str] = None

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


class Keyboard(DataModel):
    buttons: List[Button] = Field(default_factory=list, min_items=1)


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

    def __repr__(self) -> str:
        return " ".join([f"{key}='{value}'" for key, value in self.dict(exclude_none=True).items()])


class MultiMessage(Message):
    messages: Optional[List[Message]] = None
