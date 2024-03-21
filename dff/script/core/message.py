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

from dff.messengers.common.interface import MessengerInterface


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

    pass


class Command(DataModel):
    """
    This class is a subclass of DataModel and represents
    a command that can be executed in response to a user input.
    """

    pass


class Attachment(DataModel):
    pass


class CallbackQuery(Attachment):
    query_string: Optional[str]


class Location(Attachment):
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


class Contact(Attachment):
    phone_number: str
    first_name: str
    last_name: Optional[str]


class Invoice(Attachment):
    title: str
    description: str
    currency: str
    amount: int


class PollOption(DataModel):
    text: str
    votes: int


class Poll(Attachment):
    question: str
    options: List[PollOption]


class DataAttachment(Attachment):
    """
    This class represents an attachment that can be either
    a file or a URL, along with an optional ID and title.
    """

    source: Optional[Union[HttpUrl, FilePath]] = None
    id: Optional[str] = None  # id field is made separate to simplify type validation
    title: Optional[str] = None

    async def get_bytes(self, from_messenger_interface: MessengerInterface) -> Optional[bytes]:
        if self.source is None:
            await from_messenger_interface.populate_attachment(self)
        if isinstance(self.source, Path):
            with open(self.source, "rb") as file:
                return file.read()
        elif isinstance(self.source, HttpUrl):
            with urlopen(self.source.unicode_string()) as file:
                return file.read()
        else:
            return None

    def __eq__(self, other):
        if isinstance(other, DataAttachment):
            if self.id != other.id:
                return False
            if self.title != other.title:
                return False
            return True
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


class Audio(DataAttachment):
    """Represents an audio file attachment."""

    pass


class Video(DataAttachment):
    """Represents a video file attachment."""

    pass


class Animation(DataAttachment):
    """Represents an animation file attachment."""

    pass


class Image(DataAttachment):
    """Represents an image file attachment."""

    pass


class Document(DataAttachment):
    """Represents a document file attachment."""

    pass


class Button(DataModel):
    """Represents a button of an inline keyboard."""

    text: str
    data: Optional[str] = None

    @field_validator("data")
    @classmethod
    def data_length_should_be_constrained(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value_size = len(value.encode("utf-8"))
        if 1 <= value_size <= 64 and value:
            return value
        else:
            raise ValueError(f"Unexpected data length: {value_size} bytes")


class Keyboard(Attachment):
    """
    This class is an Attachment that represents a keyboard object
    that can be used for a chatbot or messaging application.
    """

    buttons: List[List[Button]] = Field(default_factory=list, min_length=1)

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
    attachments: Optional[List[Attachment]] = None
    annotations: Optional[dict] = None
    misc: Optional[dict] = None
    original_message: Optional[Any] = None
    # commands and state options are required for integration with services
    # that use an intermediate backend server, like Yandex's Alice
    # state: Optional[Session] = Session.ACTIVE
    # ui: Optional[Union[Keyboard, DataModel]] = None

    def __init__(
        self,
        text: Optional[str] = None,
        commands: Optional[List[Command]] = None,
        attachments: Optional[Attachment] = None,
        annotations: Optional[dict] = None,
        misc: Optional[dict] = None,
        **kwargs,
    ):
        super().__init__(
            text=text, commands=commands, attachments=attachments, annotations=annotations, misc=misc, **kwargs
        )

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
