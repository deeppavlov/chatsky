import datetime
import json
from typing import Any

from pydantic import BaseModel, Field, validator
from dff.core.engine.core.context import Context, get_last_index
from dff.core.pipeline import ExtraHandlerRuntimeInfo

from .utils import get_wrapper_field


class StatsRecord(BaseModel):
    context_id: str
    request_id: int
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    data_key: str
    data: dict

    @validator("data", pre=True)
    def validate_data(cls, val):
        if isinstance(val, str):
            return json.loads(val)
        return val

    @classmethod
    def from_context(cls, ctx: Context, info: ExtraHandlerRuntimeInfo, data: Any):
        context_id = str(ctx.id)
        request_id = get_last_index(ctx.requests)
        data_key = get_wrapper_field(info)
        data = data
        return cls(context_id=context_id, request_id=request_id, data_key=data_key, data=data)

    class Config:
        orm_mode = True
