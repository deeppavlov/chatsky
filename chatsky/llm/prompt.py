from typing import Optional, Union
from pydantic import BaseModel, model_validator
from chatsky.core import BaseResponse, BasePriority, AnyPriority, AnyResponse, MessageInitTypes, Message


class DesaultPositionConfig(BaseModel):
    system_prompt: float = 0
    history: float = 1
    misc_prompt: float = 2
    call_prompt: float = 3
    last_response: float = 4


class Prompt(BaseModel):
    prompt: AnyResponse
    position: Optional[AnyPriority] = None

    def __init__(
        self,
        prompt: Union[MessageInitTypes, BaseResponse],
        position: Optional[Union[float, BasePriority]] = None
    ):
        super().__init__(prompt=prompt, position=position)

    @model_validator(mode="before")
    @classmethod
    def validate_from_message(cls, data):
            # MISC: {"prompt": "message", "prompt": Message("text"), "prompt": FilledTemplate(), "prompt": Prompt(prompt=FilledTemplate(), position=-2)
            # Prompt.model_validate
        if isinstance(data, (str, Message, BaseResponse)):
            return {"prompt": data}
        return data