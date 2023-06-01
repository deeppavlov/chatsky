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
from dff.stats.utils import get_wrapper_field


class ORMRecord(BaseModel):
    class Config:
        orm_mode = True


class TraceRecord(ORMRecord):
    Timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    TraceId: str = ""
    SpanId: str = ""
    ParentSpanId: str = ""
    TraceState: str = ""
    SpanName: str = ""
    SpanKind: str = ""
    ServiceName: str = "dialog_flow_framework"
    ResourceAttributes: dict = Field(default_factory=dict)
    SpanAttributes: dict = Field(default_factory=dict)
    Duration: int = 1
    StatusCode: str = "0"
    StatusMessage: str = ""
    EventTimestamp = Field(alias="Events.Timestamp", default_factory=list)
    EventName = Field(alias="Events.Name", default_factory=list)
    EventAttributes = Field(alias="Events.Attributes", default_factory=list)
    LinkTraceId = Field(alias="Links.TraceId", default_factory=list)
    LinkSpanId = Field(alias="Links.SpanId", default_factory=list)
    LinkTraceState = Field(alias="Links.TraceState", default_factory=list)
    LinkAttributes = Field(alias="Links.Attributes", default_factory=list)

    @classmethod
    def from_context(cls, ctx: Context, info: ExtraHandlerRuntimeInfo, data: Any):
        """
        Construct a trace record from local variables of a pipeline processor function:
        context, handler information, and arbitrary json-serializeable data.
        """
        return cls(Timestamp=datetime.datetime.now())


class LogRecord(ORMRecord):
    Timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    TraceId: str = ""
    SpanId: str = ""
    TraceFlags: int = 1
    SeverityText: str = ""
    SeverityNumber: int = 1
    ServiceName: str = "dialog_flow_framework"
    Body: str = Field(default=json.dumps({}))
    ResourceAttributes: dict = Field(default_factory=dict)
    LogAttributes: dict = Field(default_factory=dict)

    @validator("Body", pre=True)
    def validate_body(cls, val):
        if isinstance(val, str):
            return json.loads(val)
        return val

    @classmethod
    def from_context(cls, ctx: Context, info: ExtraHandlerRuntimeInfo, data: Any):
        """
        Construct a log record from local variables of a pipeline processor function:
        context, handler information, and arbitrary json-serializeable data.
        """
        return cls(
            Timestamp=datetime.datetime.now(),
            LogAttributes={"context_id": ctx.id, "request_id": get_last_index(ctx.requests)},
        )
