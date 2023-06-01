"""
Clickhouse Saver
----------------
Provides the Clickhouse version of the :py:class:`.dff.stats.savers.saver.Saver`.
The class should be constructed by calling the :py:func:`~dff.stats.savers.saver_factory`
factory with specific parameters.

"""
import json
from typing import List, Tuple
from urllib import parse
import asyncio

from pydantic import validator

try:
    from httpx import AsyncClient
    from aiochclient import ChClient

    IMPORT_ERROR_MESSAGE = None
except ImportError as e:
    IMPORT_ERROR_MESSAGE = e.msg

from .saver import Saver
from ..record import LogRecord, TraceRecord


class ClickhouseTraceRecord(TraceRecord):
    @validator("Timestamp")
    def val_timestamp(cls, data):
        if not isinstance(data, str):
            return data.isoformat()
        return data


class ClickhouseLogRecord(LogRecord):
    @validator("Body", pre=True)
    def val_data(cls, data):
        if not isinstance(data, str):
            return json.dumps(data)
        return data

    @validator("Timestamp", pre=True)
    def val_timestamp(cls, data):
        if not isinstance(data, str):
            return data.isoformat()
        return data


CREATE_LOGS = """
CREATE TABLE IF NOT EXISTS {table}
(
    `Timestamp` DateTime64(9),
    `TraceId` String,
    `SpanId` String,
    `TraceFlags` UInt32,
    `SeverityText` LowCardinality(String),
    `SeverityNumber` Int32,
    `ServiceName` LowCardinality(String),
    `Body` String,
    `ResourceAttributes` Map(LowCardinality(String), String),
    `LogAttributes` Map(LowCardinality(String), String),
    INDEX idx_trace_id TraceId TYPE bloom_filter(0.001) GRANULARITY 1,
    INDEX idx_res_attr_key mapKeys(ResourceAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_res_attr_value mapValues(ResourceAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_log_attr_key mapKeys(LogAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_log_attr_value mapValues(LogAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_body Body TYPE tokenbf_v1(32768, 3, 0) GRANULARITY 1
)
ENGINE = MergeTree
PARTITION BY toDate(Timestamp)
ORDER BY (ServiceName, SeverityText, toUnixTimestamp(Timestamp), TraceId)
"""
CREATE_TRACES = """
CREATE TABLE IF NOT EXISTS {table}
(
    `Timestamp` DateTime64(9),
    `TraceId` String,
    `SpanId` String,
    `ParentSpanId` String,
    `TraceState` String,
    `SpanName` LowCardinality(String),
    `SpanKind` LowCardinality(String),
    `ServiceName` LowCardinality(String),
    `ResourceAttributes` Map(LowCardinality(String), String),
    `SpanAttributes` Map(LowCardinality(String), String),
    `Duration` Int64,
    `StatusCode` LowCardinality(String),
    `StatusMessage` String,
    `Events.Timestamp` Array(DateTime64(9)),
    `Events.Name` Array(LowCardinality(String)),
    `Events.Attributes` Array(Map(LowCardinality(String), String)),
    `Links.TraceId` Array(String),
    `Links.SpanId` Array(String),
    `Links.TraceState` Array(String),
    `Links.Attributes` Array(Map(LowCardinality(String), String)),
    INDEX idx_trace_id TraceId TYPE bloom_filter(0.001) GRANULARITY 1,
    INDEX idx_res_attr_key mapKeys(ResourceAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_res_attr_value mapValues(ResourceAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_span_attr_key mapKeys(SpanAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_span_attr_value mapValues(SpanAttributes) TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_duration Duration TYPE minmax GRANULARITY 1
)
ENGINE = MergeTree
PARTITION BY toDate(Timestamp)
ORDER BY (ServiceName, SpanName, toUnixTimestamp(Timestamp), TraceId)
"""


class ClickHouseSaver(Saver):
    """
    Saves and reads the stats dataframe from a Clickhouse database.
    The class should be constructed by calling the :py:func:`~dff.stats.savers.saver_factory`
    factory with specific parameters.

    :param path: The construction path.
        It should match the sqlalchemy :py:class:`~sqlalchemy.engine.Engine` initialization string.

        .. code-block::

            ClickHouseSaver("clickhouse://user:password@localhost:8000/default")

    :param table: Sets the name of the db table to use. Defaults to "dff_stats".
    """

    def __init__(self, path: str, logs_table: str = "otel_logs", traces_table: str = "otel_traces") -> None:
        if IMPORT_ERROR_MESSAGE is not None:
            raise ImportError(IMPORT_ERROR_MESSAGE)
        self.logs_table = logs_table
        self.traces_table = traces_table
        parsed_path = parse.urlparse(path)
        auth, _, address = parsed_path.netloc.partition("@")
        self.db = parsed_path.path.strip("/")
        self.url = parse.urlunparse(("http", address, "/", "", "", ""))
        user, _, password = auth.partition(":")
        http_client = AsyncClient()
        if not all([self.db, self.url, user, password]):
            raise ValueError("Invalid database URI or credentials")
        self.ch_client = ChClient(http_client, url=self.url, user=user, password=password, database=self.db)
        asyncio.run(self.create_table())

    async def save(self, data: List[Tuple[TraceRecord, LogRecord]]) -> None:
        if len(data) == 0:
            return

        await self.ch_client.execute(
            f"INSERT INTO {self.traces_table} VALUES",
            *[tuple(ClickhouseLogRecord.parse_obj(item[0]).dict().values()) for item in data],
        )
        await self.ch_client.execute(
            f"INSERT INTO {self.logs_table} VALUES",
            *[tuple(ClickhouseLogRecord.parse_obj(item[1]).dict().values()) for item in data],
        )

    async def load(self) -> List[Tuple[TraceRecord, LogRecord]]:
        results = []
        iterator = zip(
            self.ch_client.iterate(f"SELECT * FROM {self.traces_table}"),
            self.ch_client.iterate(f"SELECT * FROM {self.logs_table}"),
        )
        async for trace, log in iterator:
            parsed_trace = TraceRecord.parse_obj({key: trace[key] for key in trace.keys()})
            parsed_log = LogRecord.parse_obj({key: log[key] for key in log.keys()})
            results.append((parsed_trace, parsed_log))
        return results

    async def create_table(self):
        await self.ch_client.execute(CREATE_LOGS.format(table=self.logs_table))
        await self.ch_client.execute(CREATE_TRACES.format(table=self.traces_table))
