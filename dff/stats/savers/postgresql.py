"""
Postgresql
---------------------------
Provides the Postgresql version of the :py:class:`~dff.stats.savers.saver.Saver`. 
You don't need to interact with this class manually, as it will be automatically 
imported and initialized when you construct :py:class:`~dff.stats.savers.saver.Saver` with specific parameters.

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
    You don't need to interact with this class manually, as it will be automatically
    initialized when you construct :py:class:`~dff.stats.savers.saver.Saver` with specific parameters.

    Parameters
    ----------

    path: str
        | The construction path.
        | It should match the sqlalchemy :py:class:`~sqlalchemy.engine.Engine` initialization string.

        .. code-block::

            Saver("postgresql://user:password@localhost:5432/default")

    table: str
        Sets the name of the db table to use. Defaults to "dff_stats".
    """

    def __init__(self, path: str, table: str = "df_stats") -> None:
        if IMPORT_ERROR_MESSAGE is not None:
            raise ImportError(IMPORT_ERROR_MESSAGE)
        self.table = table
        self.table_exists = False
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
        if not self.table_exists:
            await self._create_table()
            self.table_exists = True

        async with self.engine.connect() as conn:
            await conn.execute(insert(self.sql_table).values([item.dict() for item in data]))
            await conn.commit()

    async def load(self) -> List[StatsRecord]:
        stats = []

        async with self.engine.connect() as conn:
            result = await conn.execute(select(self.sql_table))

        async for item in result.all():
            stats.append(StatsRecord.from_orm(item))

        return stats

    async def _create_table(self):
        def table_exists(conn):
            return inspect(conn).has_table(self.table)

        async with self.engine.connect() as conn:
            exist_result = await conn.run_sync(table_exists)
            if exist_result:
                return

            await conn.run_sync(self.metadata.create_all)
            await conn.commit()
