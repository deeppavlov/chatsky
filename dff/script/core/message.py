"""
Message
-------
The :py:class:`.Message` class is a universal data model for representing a message that should be supported by
DFF. It only contains types and properties that are compatible with most messaging services.
"""

from typing import Any, Callable, Dict, Literal, Optional, List, Union
from enum import Enum, auto
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

from pydantic import Field, field_validator, FilePath, HttpUrl, BaseModel, model_serializer, model_validator
from pydantic_core import Url

from dff.messengers.common.interface import MessengerInterface
from dff.utils.pydantic import json_pickle_serializer, json_pickle_validator


class DataModel(BaseModel, extra="allow", arbitrary_types_allowed=True):
    """
    This class is a Pydantic BaseModel that serves as a base class for all DFF models.
    """

    pass


# TODO: inline once annotated __pydantic_extra__ will be available in pydantic
def _json_extra_serializer(model: DataModel, original_serializer: Callable[[DataModel], Dict[str, Any]]) -> Dict[str, Any]:
    model_copy = model.model_copy(deep=True)
    for extra_name in model.model_extra.keys():
        delattr(model_copy, extra_name)
    model_dict = original_serializer(model_copy)
    model_dict.update(json_pickle_serializer(model.model_extra, original_serializer))
    return model_dict


# TODO: inline once annotated __pydantic_extra__ will be available in pydantic
def _json_extra_validator(model: DataModel) -> DataModel:
    model.__pydantic_extra__ = json_pickle_validator(model.__pydantic_extra__)
    return model


class Session(Enum):
    """
    An enumeration that defines two possible states of a session.
    """

    ACTIVE = auto()
    FINISHED = auto()


class Command(DataModel):
    """
    This class is a subclass of DataModel and represents
    a command that can be executed in response to a user input.
    """

    pass


class Attachment(DataModel):
    """
    """

    @model_validator(mode="after")
    def extra_validator(self) -> "Attachment":
        return _json_extra_validator(self)

    @model_serializer(mode="wrap", when_used="json")
    def extra_serializer(self, original_serializer: Callable[["Attachment"], Dict[str, Any]]) -> Dict[str, Any]:
        return _json_extra_serializer(self, original_serializer)


class CallbackQuery(Attachment):
    query_string: Optional[str]
    dff_attachment_type: Literal["callback_query"] = "callback_query"


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
    dff_attachment_type: Literal["location"] = "location"

    def __eq__(self, other):
        if isinstance(other, Location):
            return abs(self.latitude - other.latitude) + abs(self.longitude - other.longitude) < 0.00004
        return NotImplemented


class Contact(Attachment):
    phone_number: str
    first_name: str
    last_name: Optional[str]
    dff_attachment_type: Literal["contact"] = "contact"


class Invoice(Attachment):
    title: str
    description: str
    currency: str
    amount: int
    dff_attachment_type: Literal["invoice"] = "invoice"


class PollOption(DataModel):
    text: str
    votes: int = Field(default=0)
    dff_attachment_type: Literal["poll_option"] = "poll_option"


class Poll(Attachment):
    question: str
    options: List[PollOption]
    dff_attachment_type: Literal["poll"] = "poll"


class DataAttachment(Attachment):
    """
    This class represents an attachment that can be either
    a file or a URL, along with an optional ID and title.
    """

    source: Optional[Union[HttpUrl, FilePath]] = None
    cached_filename: Optional[FilePath] = None
    id: Optional[str] = None  # id field is made separate to simplify type validation
    title: Optional[str] = None
    use_cache: bool = True

    async def _cache_attachment(self, data: bytes, directory: Path) -> None:
        title = str(uuid4()) if self.title is None else self.title
        self.cached_filename = directory / title
        with open(self.cached_filename, "wb") as file:
            file.write(data)

    async def get_bytes(self, from_interface: MessengerInterface) -> Optional[bytes]:
        if isinstance(self.source, Path):
            with open(self.source, "rb") as file:
                return file.read()
        elif self.cached_filename is not None:
            with open(self.cached_filename, "rb") as file:
                return file.read()
        elif isinstance(self.source, Url):
            with urlopen(self.source.unicode_string()) as url:
                attachment_data = url.read()
        else:
            attachment_data = await from_interface.populate_attachment(self)
        if self.use_cache:
            await self._cache_attachment(attachment_data, from_interface.attachments_directory)
        return attachment_data

    def __eq__(self, other):
        if isinstance(other, DataAttachment):
            if self.id != other.id:
                return False
            if self.source != other.source:
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

    dff_attachment_type: Literal["audio"] = "audio"


class Video(DataAttachment):
    """Represents a video file attachment."""

    dff_attachment_type: Literal["video"] = "video"


class Animation(DataAttachment):
    """Represents an animation file attachment."""

    dff_attachment_type: Literal["animation"] = "animation"


class Image(DataAttachment):
    """Represents an image file attachment."""

    dff_attachment_type: Literal["image"] = "image"


class Sticker(DataAttachment):
    """Represents a sticker as a file attachment."""

    dff_attachment_type: Literal["sticker"] = "sticker"


class Document(DataAttachment):
    """Represents a document file attachment."""

    dff_attachment_type: Literal["document"] = "document"


class Message(DataModel):
    """
    Class representing a message and contains several
    class level variables to store message information.
    """

    text: Optional[str] = None
    commands: Optional[List[Command]] = None
    attachments: Optional[List[Union[CallbackQuery, Location, Contact, Invoice, Poll, Audio, Video, Animation, Image, Sticker, Document]]] = None
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

    @model_validator(mode="after")
    def extra_validator(self) -> "Message":
        return _json_extra_validator(self)

    @model_serializer(mode="wrap", when_used="json")
    def extra_serializer(self, original_serializer: Callable[["Message"], Dict[str, Any]]) -> Dict[str, Any]:
        return _json_extra_serializer(self, original_serializer)
