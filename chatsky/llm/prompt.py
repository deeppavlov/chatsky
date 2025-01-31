from typing import Optional, Union
from pydantic import BaseModel, model_validator
from chatsky.core import BaseResponse, BasePriority, AnyPriority, AnyResponse, MessageInitTypes, Message


class PositionConfig(BaseModel):
    system_prompt: float = 0
    history: float = 1
    misc_prompt: float = 2
    call_prompt: float = 3
    last_request: float = 4


class Prompt(BaseModel):
    message: AnyResponse
    position: Optional[AnyPriority] = None

    def __init__(
        self, message: Union[MessageInitTypes, BaseResponse], position: Optional[Union[float, BasePriority]] = None
    ):
        super().__init__(message=message, position=position)

    @model_validator(mode="before")
    @classmethod
    def validate_from_message(cls, data):
        if isinstance(data, (str, Message, BaseResponse)):
            return {"message": data}
        return data
