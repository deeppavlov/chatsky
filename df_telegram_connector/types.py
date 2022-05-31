"""
Types
******

This module implements local classes for compatibility with `df-generics` library.
You can use :py:class:`~TelegramResponse` class directly with the `send_response` method
that belongs to the :py:class:`connector.TelegramConnector` class.
"""
from argparse import ArgumentError
from typing import Any, List, Optional, Union
from pathlib import Path

from telebot import types
from pydantic import BaseModel, ValidationError, validator, root_validator, Field, Extra, FilePath, HttpUrl, Required

import df_generics


class AdapterModel(BaseModel):
    class Config:
        extra = Extra.ignore
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


class TelegramButton(AdapterModel):
    text: str = Field(alias="text")
    url: Optional[str] = Field(default=None, alias="source")
    callback_data: Optional[str] = Field(default=None, alias="payload")


class TelegramUI(AdapterModel):
    buttons: Optional[List[TelegramButton]] = None
    is_inline: bool = True
    keyboard: Optional[Union[types.ReplyKeyboardRemove, types.ReplyKeyboardMarkup, types.InlineKeyboardMarkup]] = None
    row_width: int = 3

    @root_validator
    def init_validator(cls, values: dict):
        if values["keyboard"] is not None:  # no changes if buttons are not required
            return values
        if not values.get("buttons"):
            raise ValueError(
                "`buttons` parameter is required, when `keyboard` is not equal to telebot.types.ReplyKeyboardRemove."
            )
        kb_args = {"row_width": values.get("row_width")}
        is_inline = values.get("is_inline")
        if is_inline:
            keyboard = types.InlineKeyboardMarkup(**kb_args)
            buttons = [types.InlineKeyboardButton(**item.dict()) for item in values["buttons"]]
        else:
            keyboard = types.ReplyKeyboardMarkup(**kb_args)
            buttons = [types.KeyboardButton(text=item.text) for item in values["buttons"]]
        keyboard.add(*buttons, row_width=values["row_width"])
        values["keyboard"] = keyboard
        return values


class TelegramAttachment(AdapterModel):
    source: Optional[Union[HttpUrl, FilePath]] = None
    id: Optional[str] = None  # id field is made separate to simplify validation.
    title: Optional[str] = None

    @root_validator
    def validate_id_or_source(cls, values):
        if bool(values["source"]) == bool(values["id"]):
            raise ArgumentError("Attachment type requires exactly one parameter, `source` or `id`.")
        return values

    @validator("source", pre=False)
    def validate_source(cls, source: Optional[Union[HttpUrl, FilePath]]):
        if not isinstance(source, Path):
            return source
        if not source.exists():
            raise OSError(f"Provided filepath {str(source)} does not exist")
        return source


class TelegramAttachments(AdapterModel):
    files: List[types.InputMedia] = Field(default_factory=list, min_items=2, max_items=10)

    @validator("files", pre=True, each_item=True, always=True)
    def cast_to_input_media(cls, file: Any):
        tg_cls = None

        if isinstance(file, df_generics.Image):
            tg_cls = types.InputMediaPhoto
        elif isinstance(file, df_generics.Audio):
            tg_cls = types.InputMediaAudio
        elif isinstance(file, df_generics.Document):
            tg_cls = types.InputMediaDocument
        elif isinstance(file, df_generics.Video):
            tg_cls = types.InputMediaVideo

        if tg_cls:
            file = tg_cls(media=file.source or file.id, caption=file.title)

        if isinstance(file, types.InputMedia):
            return file
        else:
            raise TypeError(
                """`files` field can only be set with InputMedia objects (pytelegrambotapi lib), 
                or Image, Video, Audio or Document objects (df_generics lib).
                """
            )


class TelegramResponse(AdapterModel):
    text: str = Required
    ui: Optional[TelegramUI] = None
    location: Optional[types.Location] = None
    document: Optional[TelegramAttachment] = None
    image: Optional[TelegramAttachment] = None
    video: Optional[TelegramAttachment] = None
    audio: Optional[TelegramAttachment] = None
    attachments: Optional[TelegramAttachments] = None
