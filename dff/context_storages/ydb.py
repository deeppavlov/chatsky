"""
ydb
---------------------------

| Provides the version of the :py:class:`.DBContextStorage` for YDB.

"""
import asyncio
import os
from typing import Any
from urllib.parse import urlsplit


from dff.script import Context

from .database import DBContextStorage, threadsafe_method
from .protocol import get_protocol_install_suggestion

try:
    import ydb
    from ydb.aio import Driver, SessionPool

    ydb_available = True
except ImportError:
    ydb_available = False


class YDBContextStorage(DBContextStorage):
    """
    | Version of the :py:class:`.DBContextStorage` for YDB.

    Parameters
    -----------

    path: str
        Standard sqlalchemy URI string.
        When using sqlite backend in Windows, keep in mind that you have to use double backslashes '\\'
        instead of forward slashes '/' in the file path.
    table_name: str
        The name of the table to use.
    """

    def __init__(self, path: str, table_name: str = "contexts", timeout=5):
        super(YDBContextStorage, self).__init__(path)
        protocol, netloc, self.database, _, _ = urlsplit(path)
        self.endpoint = "{}://{}".format(protocol, netloc)
        self.table_name = table_name
        if not ydb_available:
            install_suggestion = get_protocol_install_suggestion("grpc")
            raise ImportError("`ydb` package is missing.\n" + install_suggestion)

        asyncio.run(self._create_engine(timeout))

    @threadsafe_method
    async def setitem(self, key: Any, value: Context):

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
                {"$queryId": str(key), "$queryContext": value.json()},
                commit_tx=True,
            )

        return await self.pool.retry_operation(callee)

    @threadsafe_method
    async def getitem(self, key: Any) -> Context:
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

    @threadsafe_method
    async def delitem(self, key: str) -> None:
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

    @threadsafe_method
    async def contains(self, key: str) -> bool:
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

    @threadsafe_method
    async def len(self) -> int:
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

    @threadsafe_method
    async def clear_async(self) -> None:
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

    async def _create_engine(self, timeout):
        self.driver = Driver(endpoint=self.endpoint, database=self.database)
        await self.driver.wait(timeout=timeout, fail_fast=True)

        self.pool = SessionPool(self.driver, 100)

        if not await self._is_table_exists(self.pool, self.database, self.table_name):  # create table if it does not exist
            await self._create_table(self.pool, self.database, self.table_name)

    @staticmethod
    async def _is_table_exists(pool, path, table_name):
        try:

            async def callee(session):
                session.describe_table(os.path.join(path, table_name))

            await pool.retry_operation(callee)
            return True
        except ydb.SchemeError:
            return False

    @staticmethod
    async def _create_table(pool, path, table_name):
        async def callee(session):
            session.create_table(
                "/".join([path, table_name]),
                ydb.TableDescription()
                .with_column(ydb.Column("id", ydb.OptionalType(ydb.PrimitiveType.Utf8)))
                .with_column(ydb.Column("context", ydb.OptionalType(ydb.PrimitiveType.Json)))
                .with_primary_key("id"),
            )

        return await pool.retry_operation(callee)
