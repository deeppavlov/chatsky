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

from pydantic import BaseModel, Field, JsonValue, field_validator, FilePath, HttpUrl, model_serializer, model_validator
from pydantic_core import Url

from dff.messengers.common.interface import MessengerInterface
from dff.utils.pydantic import JSONSerializableDict, SerializableVaue, json_pickle_serializer, json_pickle_validator


class DataModel(BaseModel, extra="allow", arbitrary_types_allowed=True):
    """
    This class is a Pydantic BaseModel that can have any type and number of extras.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# TODO: inline once annotated __pydantic_extra__ will be available in pydantic
def _json_extra_serializer(model: DataModel, original_serializer: Callable[[DataModel], JsonValue]) -> JsonValue:
    """
    Serialize model along with the `extras` field: i.e. all the fields not listed in the model.
    This function should be used as "wrap" serializer.

    :param model: Pydantic model for serialization.
    :param original_serializer: Function originally used for serialization by Pydantic.
    :return: Serialized model.
    """

    model_copy = model.model_copy(deep=True)
    for extra_name in model.model_extra.keys():
        delattr(model_copy, extra_name)
    model_dict = original_serializer(model_copy)
    model_dict.update(json_pickle_serializer(model.model_extra, original_serializer))
    return model_dict


# TODO: inline once annotated __pydantic_extra__ will be available in pydantic
def _json_extra_validator(model: DataModel) -> DataModel:
    """
    Validate model along with the `extras` field: i.e. all the fields not listed in the model.
    This function should be used as "after" validator.

    :param model: Pydantic model for validation.
    :return: Validated model.
    """

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
    DFF Message attachment base class.
    It is capable of serializing and validating all the model fields to JSON.
    """

    @model_validator(mode="after")
    def extra_validator(self) -> "Attachment":
        return _json_extra_validator(self)

    @model_serializer(mode="wrap", when_used="json")
    def extra_serializer(self, original_serializer: Callable[["Attachment"], Dict[str, Any]]) -> Dict[str, Any]:
        return _json_extra_serializer(self, original_serializer)


class CallbackQuery(Attachment):
    """
    This class is a data model that represents a callback query attachment.
    It is sent as a response to non-message events, e.g. keyboard UI interactions.
    It has query string attribute, that represents the response data string.
    """

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
    """
    This class is a data model that represents a contact.
    It includes phone number, and user first and last name.
    """

    phone_number: str
    first_name: str
    last_name: Optional[str]
    dff_attachment_type: Literal["contact"] = "contact"


class Invoice(Attachment):
    """
    This class is a data model that represents an invoice.
    It includes title, description, currency name and amount.
    """

    title: str
    description: str
    currency: str
    amount: int
    dff_attachment_type: Literal["invoice"] = "invoice"


class PollOption(DataModel):
    """
    This class is a data model that represents a poll option.
    It includes the option name and votes number.
    """

    text: str
    votes: int = Field(default=0)
    dff_attachment_type: Literal["poll_option"] = "poll_option"


class Poll(Attachment):
    """
    This class is a data model that represents a poll.
    It includes a list of poll options.
    """

    question: str
    options: List[PollOption]
    dff_attachment_type: Literal["poll"] = "poll"


class DataAttachment(Attachment):
    """
    This class represents an attachment that can be either
    a file or a URL, along with an optional ID and title.
    This attachment can also be optionally cached for future use.
    """

    source: Optional[Union[HttpUrl, FilePath]] = None
    cached_filename: Optional[FilePath] = None
    id: Optional[str] = None
    title: Optional[str] = None
    use_cache: bool = True

    async def _cache_attachment(self, data: bytes, directory: Path) -> None:
        """
        Cache attachment, save bytes into a file.

        :param data: attachment data bytes.
        :param directory: cache file where attachment will be saved.
        """

        title = str(uuid4()) if self.title is None else self.title
        self.cached_filename = directory / title
        with open(self.cached_filename, "wb") as file:
            file.write(data)

    async def get_bytes(self, from_interface: MessengerInterface) -> Optional[bytes]:
        """
        Download attachment bytes.
        If the attachment is represented by URL or saved in a file,
        it will be downloaded or read automatically.
        Otherwise, a :py:meth:`~dff.messengers.common.MessengerInterface.populate_attachment`
        will be used for receiving attachment bytes by ID and title.

        :param from_interface: messenger interface the attachment was received from.
        """

        if isinstance(self.source, Path):
            with open(self.source, "rb") as file:
                return file.read()
        elif self.use_cache and self.cached_filename is not None:
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


class VoiceMessage(DataAttachment):
    """Represents a voice message."""

    dff_attachment_type: Literal["voice_message"] = "voice_message"


class VideoMessage(DataAttachment):
    """Represents a video message."""

    dff_attachment_type: Literal["video_message"] = "video_message"


class Message(DataModel):
    """
    Class representing a message and contains several
    class level variables to store message information.

    It includes message text, list of commands included in the message,
    list of attachments, annotations, MISC dictionary (that consists of
    user-defined parameters) and original message field that somehow represent
    the update received from messenger interface API.
    """

    text: Optional[str] = None
    commands: Optional[List[Command]] = None
    attachments: Optional[
        List[
            Union[
                CallbackQuery,
                Location,
                Contact,
                Invoice,
                Poll,
                Audio,
                Video,
                Animation,
                Image,
                Sticker,
                Document,
                VoiceMessage,
                VideoMessage,
            ]
        ]
    ] = None
    annotations: Optional[JSONSerializableDict] = None
    misc: Optional[JSONSerializableDict] = None
    original_message: Optional[SerializableVaue] = None

    def __init__(
        self,
        text: Optional[str] = None,
        commands: Optional[List[Command]] = None,
        attachments: Optional[
            List[
                Union[
                    CallbackQuery,
                    Location,
                    Contact,
                    Invoice,
                    Poll,
                    Audio,
                    Video,
                    Animation,
                    Image,
                    Sticker,
                    Document,
                    VoiceMessage,
                    VideoMessage,
                ]
            ]
        ] = None,
        annotations: Optional[JSONSerializableDict] = None,
        misc: Optional[JSONSerializableDict] = None,
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
