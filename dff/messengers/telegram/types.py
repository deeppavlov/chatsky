"""
Types
--------------
This module implements local classes that help cast generic types from `dff` to native Telegram types.
"""
from typing import Any, List, Optional, Union

from telebot import types
from pydantic import BaseModel, validator, root_validator, Field, Extra, FilePath, HttpUrl, Required

from dff.script.responses import Image, Audio, Document, Video, Response, Location


class TelegramDataModel(BaseModel):
    class Config:
        extra = Extra.ignore
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


class TelegramButton(TelegramDataModel):
    text: str = Field(alias="text")
    url: Optional[str] = Field(default=None, alias="source")
    callback_data: Optional[str] = Field(default=None, alias="payload")


class TelegramUI(TelegramDataModel):
    buttons: Optional[List[TelegramButton]] = None
    is_inline: bool = True
    keyboard: Optional[Union[types.ReplyKeyboardRemove, types.ReplyKeyboardMarkup, types.InlineKeyboardMarkup]] = None
    row_width: int = 3

    @root_validator
    def init_validator(cls, values: dict):
        if values["keyboard"] is not None:  # no changes if buttons are not required
            return values
        if not values.get("buttons"):
            raise ValueError("`buttons` parameter is required, when `keyboard` is None.")
        keyboard_kwargs = {"row_width": values.get("row_width")}
        is_inline = values.get("is_inline")
        if is_inline:
            keyboard = types.InlineKeyboardMarkup(**keyboard_kwargs)
            buttons = [types.InlineKeyboardButton(**item.dict()) for item in values["buttons"]]
        else:
            keyboard = types.ReplyKeyboardMarkup(**keyboard_kwargs)
            buttons = [types.KeyboardButton(text=item.text) for item in values["buttons"]]
        keyboard.add(*buttons, row_width=values["row_width"])
        values["keyboard"] = keyboard
        return values


class TelegramAttachment(TelegramDataModel):
    source: Optional[Union[HttpUrl, FilePath]] = None
    id: Optional[str] = None  # id field is made separate to simplify validation.
    title: Optional[str] = None

    @root_validator(pre=True)
    def validate_id_or_source(cls, values):
        if bool(values.get("source")) == bool(values.get("id")):
            raise TypeError("Attachment type requires exactly one parameter, `source` or `id`.")
        return values


class TelegramAttachments(TelegramDataModel):
    files: List[types.InputMedia] = Field(default_factory=list, min_items=2, max_items=10)

    @validator("files", pre=True, each_item=True, always=True)
    def cast_to_input_media_type(cls, file: Any):
        cast_to_media_type = None

        if isinstance(file, Image):
            cast_to_media_type = types.InputMediaPhoto
        elif isinstance(file, Audio):
            cast_to_media_type = types.InputMediaAudio
        elif isinstance(file, Document):
            cast_to_media_type = types.InputMediaDocument
        elif isinstance(file, Video):
            cast_to_media_type = types.InputMediaVideo

        if cast_to_media_type:
            file = cast_to_media_type(media=file.source or file.id, caption=file.title)
        return file


class TelegramResponse(Response, TelegramDataModel):
    text: str = Required
    ui: Optional[TelegramUI] = None
    location: Optional[types.Location] = None
    document: Optional[TelegramAttachment] = None
    image: Optional[TelegramAttachment] = None
    video: Optional[TelegramAttachment] = None
    audio: Optional[TelegramAttachment] = None
    attachments: Optional[TelegramAttachments] = None

    @validator("location", pre=True, always=True)
    def validate_location(cls, val: Any):
        if isinstance(val, Location):
            return types.Location(longitude=val.longitude, latitude=val.latitude)
        return val
