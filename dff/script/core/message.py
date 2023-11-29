"""
Message
-------
The :py:class:`.Message` class is a universal data model for representing a message that should be supported by
DFF. It only contains types and properties that are compatible with most messaging services.
"""
from typing import Any, Optional, List, Union
from enum import Enum, auto
from pathlib import Path
from urllib.request import urlopen

from pydantic import field_validator, Field, FilePath, HttpUrl, BaseModel, model_validator


class Session(Enum):
    """
    An enumeration that defines two possible states of a session.
    """

    ACTIVE = auto()
    FINISHED = auto()


class DataModel(BaseModel, extra="allow", arbitrary_types_allowed=True):
    """
    This class is a Pydantic BaseModel that serves as a base class for all DFF models.
    """

    ...


class Command(DataModel):
    """
    This class is a subclass of DataModel and represents
    a command that can be executed in response to a user input.
    """

    ...


class Location(DataModel):
    """
    This class is a data model that represents a geographical
    location on the Earth's surface.
    It has two attributes, longitude and latitude, both of which are float values.
    If the absolute difference between the latitude and longitude values of the two
    locations is less than 0.00004, they are considered equal.
    """

    longitude: float
    latitude: float

    def __eq__(self, other):
        if isinstance(other, Location):
            return abs(self.latitude - other.latitude) + abs(self.longitude - other.longitude) < 0.00004
        return NotImplemented


class Attachment(DataModel):
    """
    This class represents an attachment that can be either
    a file or a URL, along with an optional ID and title.
    """

    source: Optional[Union[HttpUrl, FilePath]] = None
    id: Optional[str] = None  # id field is made separate to simplify type validation
    title: Optional[str] = None

    def get_bytes(self) -> Optional[bytes]:
        if self.source is None:
            return None
        if isinstance(self.source, Path):
            with open(self.source, "rb") as file:
                return file.read()
        else:
            with urlopen(self.source.unicode_string()) as file:
                return file.read()

    def __eq__(self, other):
        if isinstance(other, Attachment):
            if self.title != other.title:
                return False
            if self.id != other.id:
                return False
            return self.get_bytes() == other.get_bytes()
        return NotImplemented

    @model_validator(mode="before")
    @classmethod
    def validate_source_or_id(cls, values: dict):
        if not isinstance(values, dict):
            raise AssertionError(f"Invalid constructor parameters: {str(values)}")
        if bool(values.get("source")) == bool(values.get("id")):
            raise AssertionError("Attachment type requires exactly one parameter, `source` or `id`, to be set.")
        return values

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, value):
        if isinstance(value, Path):
            return Path(value)
        return value


class Audio(Attachment):
    """Represents an audio file attachment."""

    pass


class Video(Attachment):
    """Represents a video file attachment."""

    pass


class Image(Attachment):
    """Represents an image file attachment."""

    pass


class Document(Attachment):
    """Represents a document file attachment."""

    pass


class Attachments(DataModel):
    """This class is a data model that represents a list of attachments."""

    files: List[Attachment] = Field(default_factory=list)

    def __eq__(self, other):
        if isinstance(other, Attachments):
            return self.files == other.files
        return NotImplemented


class Link(DataModel):
    """This class is a DataModel representing a hyperlink."""

    source: HttpUrl
    title: Optional[str] = None

    @property
    def html(self):
        return f'<a href="{self.source}">{self.title if self.title else self.source}</a>'


class Button(DataModel):
    """
    This class allows for the creation of a button object
    with a source URL, a text description, and a payload.
    """

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
    """
    This class is a DataModel that represents a keyboard object
    that can be used for a chatbot or messaging application.
    """

    buttons: List[Button] = Field(default_factory=list, min_length=1)

    def __eq__(self, other):
        if isinstance(other, Keyboard):
            return self.buttons == other.buttons
        return NotImplemented


class Message(DataModel):
    """
    Class representing a message and contains several
    class level variables to store message information.
    """

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
            for field in self.model_fields:
                if field not in other.model_fields:
                    return False
                if self.__getattribute__(field) != other.__getattribute__(field):
                    return False
            return True
        return NotImplemented

    def __repr__(self) -> str:
        return " ".join([f"{key}='{value}'" for key, value in self.model_dump(exclude_none=True).items()])


class MultiMessage(Message):
    """This class represents a message that contains multiple sub-messages."""

    messages: Optional[List[Message]] = None
