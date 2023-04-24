"""
Record
-------
The following module defines a data model for a standard database record
persisted by :py:mod:`~dff.stats`.

"""
import datetime
import json
from typing import Any

from pydantic import BaseModel, Field, validator
from dff.script.core.context import Context, get_last_index
from dff.pipeline import ExtraHandlerRuntimeInfo

from .utils import get_wrapper_field


class StatsRecord(BaseModel):
    """
    The uniform statistics record model.
    Each record is associated with a `context_id` (user)
    and `record_id` (turn). It also holds a timestamp
    of when it was recorded. The other data is saved to
    the database as JSON.
    """

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
        """
        Construct a stats record from local variables of a pipeline processor function:
        context, handler information, and arbitrary json-serializeable data.
        """
        context_id = str(ctx.id)
        request_id = get_last_index(ctx.requests)
        data_key = get_wrapper_field(info)
        return cls(context_id=context_id, request_id=request_id, data_key=data_key, data=data)

    class Config:
        orm_mode = True
