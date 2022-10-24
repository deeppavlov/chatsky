"""
Dialog Flow Generics
*************

This module contains a universal response model that should be supported in all add-ons for df-engine.
It only contains types and properties that are compatible with most messaging services.
On the other hand, it can support service-specific ui models.
"""
import os
from typing import Any, Dict, Optional, List, Union
from enum import Enum, auto

from pydantic import Extra, Field, ValidationError, root_validator, FilePath, HttpUrl, BaseModel as PydanticBaseModel


class Session(Enum):
    ACTIVE = auto()
    FINISHED = auto()


class BaseModel(PydanticBaseModel):
    class Config:
        extra = Extra.allow


class Command(BaseModel):
    command: str = ...


class Location(BaseModel):
    longitude: float = ...
    latitude: float = ...


class Attachment(BaseModel):
    source: Optional[Union[HttpUrl, FilePath]] = None
    id: Optional[str] = None  # id field is made separate to simplify type validation
    title: Optional[str] = None

    @root_validator
    def validate_source_or_id(cls, values):
        if bool(values["source"]) == bool(values["id"]):
            raise ValidationError("Attachment type requires exactly one parameter, `source` or `id`, to be set.")
        return values


class Audio(Attachment):
    pass


class Video(Attachment):
    pass


class Image(Attachment):
    pass


class Document(Attachment):
    pass


class Attachments(BaseModel):
    files: List[Attachment] = Field(default_factory=list, min_items=2, max_items=10)


class Link(BaseModel):
    source: HttpUrl = ...
    title: Optional[str] = None

    @property
    def html(self):
        return f'<a href="{self.source}">{self.title if self.title else self.source}</a>'


class Button(BaseModel):
    source: Optional[HttpUrl] = None
    text: str = ...
    payload: Optional[Any] = None


class Keyboard(BaseModel):
    buttons: List[Button] = Field(default_factory=list, min_items=1)


class Response(BaseModel):
    text: str = ...
    ui: Optional[Union[Keyboard, BaseModel]] = None
    document: Optional[Document] = None
    image: Optional[Image] = None
    attachments: Optional[Attachments] = None
    video: Optional[Video] = None
    audio: Optional[Audio] = None
    # commands and state options are required for integration with services
    # that use an intermediate backend server, like Yandex's Alice
    commands: Optional[List[Command]] = None
    state: Optional[Session] = Session.ACTIVE
    
    def __init__(self, text: str, *, **data) -> None:
        super().__init__(text=text, **data)
