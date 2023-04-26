"""
Postgresql Saver
----------------
Provides the Postgresql version of the :py:class:`~dff.stats.savers.saver.Saver`.
The class should be constructed by calling the :py:func:`~dff.stats.savers.saver_factory`
factory with specific parameters.

"""
from typing import List
from urllib import parse

try:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import inspect, Table, MetaData, Column, String, Integer, JSON, DateTime, select, insert

    IMPORT_ERROR_MESSAGE = None
except ImportError as e:
    IMPORT_ERROR_MESSAGE = e.msg

from .saver import Saver
from ..record import StatsRecord


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

    def __init__(self, path: str, table: str = "dff_stats") -> None:
        if IMPORT_ERROR_MESSAGE is not None:
            raise ImportError(IMPORT_ERROR_MESSAGE)
        self.table = table
        self._table_exists = False
        parsed_path = parse.urlparse(path)
        self.engine = create_async_engine(parse.urlunparse([(parsed_path.scheme + "+asyncpg"), *parsed_path[1:]]))
        self.metadata = MetaData()
        self.sql_table = Table(
            self.table,
            self.metadata,
            Column("context_id", String),
            Column("request_id", Integer),
            Column("timestamp", DateTime),
            Column("data_key", String),
            Column("data", JSON),
        )

    async def save(self, data: List[StatsRecord]) -> None:
        if not self._table_exists:  # check the flag each time to keep the constructor synchronous
            raise RuntimeError(f"Table {self.table} does not exist.")
        if len(data) == 0:
            return
        async with self.engine.connect() as conn:
            await conn.execute(insert(self.sql_table).values([item.dict() for item in data]))
            await conn.commit()

    async def load(self) -> List[StatsRecord]:
        if not self._table_exists:  # check the flag each time to keep the constructor synchronous
            raise RuntimeError(f"Table {self.table} does not exist.")
        stats = []

        async with self.engine.connect() as conn:
            result = await conn.execute(select(self.sql_table))

        for item in result.all():
            stats.append(StatsRecord.from_orm(item))

        return stats

    async def create_table(self):
        def table_exists(conn):
            return inspect(conn).has_table(self.table)

        async with self.engine.connect() as conn:
            exist_result = await conn.run_sync(table_exists)
            if exist_result:
                self._table_exists = True
                return

            await conn.run_sync(self.metadata.create_all)
            await conn.commit()

        self._table_exists = True
