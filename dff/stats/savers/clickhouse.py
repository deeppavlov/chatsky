"""
Clickhouse Saver
----------------
Provides the Clickhouse version of the :py:class:`.dff.stats.savers.saver.Saver`.
The class should be constructed by calling the :py:func:`~dff.stats.savers.saver_factory`
factory with specific parameters.

"""
import json
from typing import List
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
from ..record import StatsRecord


class CHItem(StatsRecord):
    """
    This class preemptively converts record data to JSON
    for compliance with Clickhouse Driver restrictions.
    """

    timestamp: str
    data: str

    @validator("data", pre=True)
    def val_data(cls, data):
        if not isinstance(data, str):
            return json.dumps(data)
        return data

    @validator("timestamp", pre=True)
    def val_timestamp(cls, data):
        if not isinstance(data, str):
            return data.isoformat()
        return data


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

    def __init__(self, path: str, table: str = "dff_stats") -> None:
        if IMPORT_ERROR_MESSAGE is not None:
            raise ImportError(IMPORT_ERROR_MESSAGE)
        self.table = table
        parsed_path = parse.urlparse(path)
        auth, _, address = parsed_path.netloc.partition("@")
        self.db = parsed_path.path.strip("/")
        self.url = parse.urlunparse(("http", address, "/", "", "", ""))
        user, _, password = auth.partition(":")
        http_client = AsyncClient()
        if not all([self.db, self.url, user, password]):
            raise ValueError("Invalid database URI or credentials")
        self.ch_client = ChClient(http_client, url=self.url, user=user, password=password, database=self.db)
        self._table_exists = False
        asyncio.run(self.create_table())

    async def save(self, data: List[StatsRecord]) -> None:
        if not self._table_exists:  # check the flag each time to keep the constructor synchronous
            raise RuntimeError(f"Table {self.table} does not exist.")

        if len(data) == 0:
            return

        await self.ch_client.execute(
            f"INSERT INTO {self.table} VALUES", *[tuple(CHItem.parse_obj(item).dict().values()) for item in data]
        )

    async def load(self) -> List[StatsRecord]:
        if not self._table_exists:  # check the flag each time to keep the constructor synchronous
            raise RuntimeError(f"Table {self.table} does not exist.")

        results = []
        async for row in self.ch_client.iterate(f"SELECT * FROM {self.table}"):
            results.append(StatsRecord.parse_obj({key: row[key] for key in row.keys()}))
        return results

    async def create_table(self):
        await self.ch_client.execute(
            f"CREATE TABLE if not exists {self.table} ("
            "context_id String, "
            "request_id Int32, "
            "timestamp DateTime64(6), "
            "data_key String, "
            "data String"
            ") ENGINE = Memory"
        )
        self._table_exists = True
