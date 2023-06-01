"""
Postgresql Saver
----------------
Provides the Postgresql version of the :py:class:`~dff.stats.savers.saver.Saver`.
The class should be constructed by calling the :py:func:`~dff.stats.savers.saver_factory`
factory with specific parameters.

"""
from typing import List, Tuple
from urllib import parse
import asyncio

try:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import inspect, Table, MetaData, Column, String, Integer, JSON, DateTime, select, insert
    from sqlalchemy.dialects.postgresql import HSTORE, ARRAY

    IMPORT_ERROR_MESSAGE = None
except ImportError as e:
    IMPORT_ERROR_MESSAGE = e.msg

from .saver import Saver
from ..record import TraceRecord, LogRecord


LOG_COLUMNS = [
    Column("Timestamp", DateTime),
    Column("TraceId", String),
    Column("SpanId", String),
    Column("TraceFlags", Integer),
    Column("SeverityText", String),
    Column("SeverityNumber", Integer),
    Column("ServiceName", String),
    Column("Body", String),
    Column("ResourceAttributes", HSTORE),
    Column("LogAttributes", HSTORE),
]
TRACE_COLUMNS = [
    Column("Timestamp", DateTime),
    Column("TraceId", String),
    Column("SpanId", String),
    Column("ParentSpanId", String),
    Column("TraceState", String),
    Column("SpanName", String),
    Column("SpanKind", String),
    Column("ServiceName", String),
    Column("ResourceAttributes", HSTORE),
    Column("SpanAttributes", HSTORE),
    Column("Duration", Integer),
    Column("StatusCode", String),
    Column("StatusMessage", String),
    Column("Events.Timestamp", ARRAY(DateTime)),
    Column("Events.Name", ARRAY(String)),
    Column("Events.Attributes", ARRAY(HSTORE)),
    Column("Links.TraceId", ARRAY(String)),
    Column("Links.SpanId", ARRAY(String)),
    Column("Links.TraceState", ARRAY(String)),
    Column("Links.Attributes", ARRAY(HSTORE)),
]


class PostgresSaver(Saver):
    """
    Saves the stats dataframe to - and reads from a Postgresql database.
    The class should be constructed by calling the :py:func:`~dff.stats.savers.saver_factory`
    factory with specific parameters.

    :param path: The construction path.
        It should match the sqlalchemy :py:class:`~sqlalchemy.engine.Engine` initialization string.

        .. code-block::

            Saver("postgresql://user:password@localhost:5432/default")

    :param table: Sets the name of the db table to use. Defaults to "dff_stats".
    """

    def __init__(self, path: str, logs_table: str = "otel_logs", traces_table: str = "otel_traces") -> None:
        if IMPORT_ERROR_MESSAGE is not None:
            raise ImportError(IMPORT_ERROR_MESSAGE)
        self.logs_tablename = logs_table
        self.traces_tablename = traces_table
        self._table_exists = False
        parsed_path = parse.urlparse(path)
        self.engine = create_async_engine(parse.urlunparse([(parsed_path.scheme + "+asyncpg"), *parsed_path[1:]]))
        self.metadata = MetaData()
        self.logs_table = Table(self.logs_tablename, self.metadata, *LOG_COLUMNS)
        self.traces_table = Table(self.traces_tablename, self.metadata, *TRACE_COLUMNS)
        asyncio.run(self.create_table())

    async def save(self, data: List[Tuple[TraceRecord, LogRecord]]) -> None:
        if len(data) == 0:
            return
        async with self.engine.connect() as conn:
            await conn.execute(insert(self.traces_table).values([item[0].dict(by_alias=True) for item in data]))
            await conn.execute(insert(self.logs_table).values([item[1].dict(by_alias=True) for item in data]))
            await conn.commit()

    async def load(self) -> List[Tuple[TraceRecord, LogRecord]]:
        stats = []

        async with self.engine.connect() as conn:
            trace_select = await conn.execute(select(self.traces_table))
            log_select = await conn.execute(select(self.logs_table))

        for trace, log in zip(trace_select, log_select):
            stats.append((TraceRecord.from_orm(trace), LogRecord.from_orm(log)))

        return stats

    async def create_table(self):
        def tables_exists(conn):
            logs_exist = inspect(conn).has_table(self.logs_tablename)
            traces_exist = inspect(conn).has_table(self.traces_tablename)
            return logs_exist and traces_exist

        async with self.engine.connect() as conn:
            exist_result = await conn.run_sync(tables_exists)
            if exist_result:
                return

            await conn.run_sync(self.metadata.create_all)
            await conn.commit()
