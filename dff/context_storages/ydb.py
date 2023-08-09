"""
Yandex DB
---------
The Yandex DB module provides a version of the :py:class:`.DBContextStorage` class that designed to work with
Yandex and other databases. Yandex DataBase is a fully-managed cloud-native SQL service that makes it easy to set up,
operate, and scale high-performance and high-availability databases for your applications.

The Yandex DB module uses the Yandex Cloud SDK, which is a python library that allows you to work
with Yandex Cloud services using python. This allows the DFF to easily integrate with the Yandex DataBase and
take advantage of the scalability and high-availability features provided by the service.
"""
import asyncio
import os
from typing import Hashable
from urllib.parse import urlsplit


from dff.script import Context

from .database import DBContextStorage
from .protocol import get_protocol_install_suggestion

try:
    import ydb
    import ydb.aio

    ydb_available = True
except ImportError:
    ydb_available = False


class YDBContextStorage(DBContextStorage):
    """
    Version of the :py:class:`.DBContextStorage` for YDB.

    :param path: Standard sqlalchemy URI string.
        When using sqlite backend in Windows, keep in mind that you have to use double backslashes '\\'
        instead of forward slashes '/' in the file path.
    :param table_name: The name of the table to use.
    """

    def __init__(self, path: str, table_name: str = "contexts", timeout=5):
        DBContextStorage.__init__(self, path)
        protocol, netloc, self.database, _, _ = urlsplit(path)
        self.endpoint = "{}://{}".format(protocol, netloc)
        self.table_name = table_name
        if not ydb_available:
            install_suggestion = get_protocol_install_suggestion("grpc")
            raise ImportError("`ydb` package is missing.\n" + install_suggestion)
        self.driver, self.pool = asyncio.run(_init_drive(timeout, self.endpoint, self.database, self.table_name))

    async def set_item_async(self, key: Hashable, value: Context):
        value = value if isinstance(value, Context) else Context.cast(value)

        async def callee(session):
            query = """
                PRAGMA TablePathPrefix("{}");
                DECLARE $queryId AS Utf8;
                DECLARE $queryContext AS Json;
                UPSERT INTO {}
                (
                    id,
                    context
                )
                VALUES
                (
                    $queryId,
                    $queryContext
                );
                """.format(
                self.database, self.table_name
            )
            prepared_query = await session.prepare(query)

            await session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                {"$queryId": str(key), "$queryContext": value.model_dump_json()},
                commit_tx=True,
            )

        return await self.pool.retry_operation(callee)

    async def get_item_async(self, key: Hashable) -> Context:
        async def callee(session):
            query = """
                PRAGMA TablePathPrefix("{}");
                DECLARE $queryId AS Utf8;
                SELECT
                    id,
                    context
                FROM {}
                WHERE id = $queryId;
                """.format(
                self.database, self.table_name
            )
            prepared_query = await session.prepare(query)

            result_sets = await session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                {
                    "$queryId": str(key),
                },
                commit_tx=True,
            )
            if result_sets[0].rows:
                return Context.cast(result_sets[0].rows[0].context)
            else:
                raise KeyError

        return await self.pool.retry_operation(callee)

    async def del_item_async(self, key: Hashable):
        async def callee(session):
            query = """
                PRAGMA TablePathPrefix("{}");
                DECLARE $queryId AS Utf8;
                DELETE
                FROM {}
                WHERE
                    id = $queryId
                ;
                """.format(
                self.database, self.table_name
            )
            prepared_query = await session.prepare(query)

            await session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                {"$queryId": str(key)},
                commit_tx=True,
            )

        return await self.pool.retry_operation(callee)

    async def contains_async(self, key: Hashable) -> bool:
        async def callee(session):
            # new transaction in serializable read write mode
            # if query successfully completed you will get result sets.
            # otherwise exception will be raised
            query = """
                PRAGMA TablePathPrefix("{}");
                DECLARE $queryId AS Utf8;
                SELECT
                    id,
                    context
                FROM {}
                WHERE id = $queryId;
                """.format(
                self.database, self.table_name
            )
            prepared_query = await session.prepare(query)

            result_sets = await session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                {
                    "$queryId": str(key),
                },
                commit_tx=True,
            )
            return len(result_sets[0].rows) > 0

        return await self.pool.retry_operation(callee)

    async def len_async(self) -> int:
        async def callee(session):
            query = """
                PRAGMA TablePathPrefix("{}");
                SELECT
                    COUNT(*) as cnt
                FROM {}
                """.format(
                self.database, self.table_name
            )
            prepared_query = await session.prepare(query)

            result_sets = await session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                commit_tx=True,
            )
            return result_sets[0].rows[0].cnt

        return await self.pool.retry_operation(callee)

    async def clear_async(self):
        async def callee(session):
            query = """
                PRAGMA TablePathPrefix("{}");
                DECLARE $queryId AS Utf8;
                DELETE
                FROM {}
                ;
                """.format(
                self.database, self.table_name
            )
            prepared_query = await session.prepare(query)

            await session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                {},
                commit_tx=True,
            )

        return await self.pool.retry_operation(callee)


async def _init_drive(timeout: int, endpoint: str, database: str, table_name: str):
    driver = ydb.aio.Driver(endpoint=endpoint, database=database)
    await driver.wait(fail_fast=True, timeout=timeout)

    pool = ydb.aio.SessionPool(driver, size=10)

    if not await _is_table_exists(pool, database, table_name):  # create table if it does not exist
        await _create_table(pool, database, table_name)
    return driver, pool


async def _is_table_exists(pool, path, table_name) -> bool:
    try:

        async def callee(session):
            await session.describe_table(os.path.join(path, table_name))

        await pool.retry_operation(callee)
        return True
    except ydb.SchemeError:
        return False


async def _create_table(pool, path, table_name):
    async def callee(session):
        await session.create_table(
            "/".join([path, table_name]),
            ydb.TableDescription()
            .with_column(ydb.Column("id", ydb.OptionalType(ydb.PrimitiveType.Utf8)))
            .with_column(ydb.Column("context", ydb.OptionalType(ydb.PrimitiveType.Json)))
            .with_primary_key("id"),
        )

    return await pool.retry_operation(callee)
