"""
Record
-------
The following module defines a data model for a standard database record
persisted by :py:mod:`~dff.stats`.

"""
from uuid import uuid4
import datetime
import json
from typing import Any

from pydantic import BaseModel, Field, validator
from dff.script.core.context import Context, get_last_index
from dff.pipeline import ExtraHandlerRuntimeInfo


class ORMRecord(BaseModel):
    class Config:
        orm_mode = True


class StatsTraceRecord(ORMRecord):
    Timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    TraceId: str = Field(default_factory=uuid4)
    SpanId: str = Field(default_factory=uuid4)
    ParentSpanId: str = ""
    TraceState: str = ""
    SpanName: str = ""
    SpanKind: str = "INTERNAL"
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

        :param ctx: Request con[text.
        :param info: Extra handler runtime info.
        :param data: Target data.
        """
        return cls(Timestamp=datetime.datetime.now(), SpanName=data.get("data_key", ""))


class StatsLogRecord(ORMRecord):
    Timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    TraceId: str = ""
    SpanId: str = ""
    TraceFlags: int = 1
    SeverityText: str = ""
    SeverityNumber: int = 1
    ServiceName: str = "dialog_flow_framework"
    Body: dict = Field(default_factory=dict)
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

        :param ctx: Request context.
        :param info: Extra handler runtime info.
        :param data: Target data.
        """
        return cls(
            Timestamp=datetime.datetime.now(),
            Body=data,
            LogAttributes={"context_id": ctx.id, "request_id": get_last_index(ctx.requests)},
        )
