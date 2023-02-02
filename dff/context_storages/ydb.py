"""
Yandex DB
---------
Provides the version of the :py:class:`.DBContextStorage` for Yandex DataBase.
"""
import os
from urllib.parse import urlsplit


from dff.script import Context

from .database import DBContextStorage, threadsafe_method
from .protocol import get_protocol_install_suggestion

try:
    import ydb

    ydb_available = True
except ImportError:
    ydb_available = False


class YDBContextStorage(DBContextStorage):
    """
    | Version of the :py:class:`.DBContextStorage` for YDB.

    :param path: Standard sqlalchemy URI string.
        When using sqlite backend in Windows, keep in mind that you have to use double backslashes '\\'
        instead of forward slashes '/' in the file path.
    :type path: str
    :param table_name: The name of the table to use.
    :type table_name: str
    """

    def __init__(self, path: str, table_name: str = "contexts", timeout=5):
        super(YDBContextStorage, self).__init__(path)
        protocol, netloc, self.database, _, _ = urlsplit(path)
        self.endpoint = "{}://{}".format(protocol, netloc)
        self.table_name = table_name
        if not ydb_available:
            install_suggestion = get_protocol_install_suggestion("grpc")
            raise ImportError("`ydb` package is missing.\n" + install_suggestion)

        self.driver = ydb.Driver(endpoint=self.endpoint, database=self.database)
        self.driver.wait(timeout=timeout, fail_fast=True)

        self.pool = ydb.SessionPool(self.driver)

        if not self._is_table_exists(self.pool, self.database, self.table_name):  # create table if it does not exist
            self._create_table(self.pool, self.database, self.table_name)

    @threadsafe_method
    def __setitem__(self, key: str, value: Context) -> None:

        value = value if isinstance(value, Context) else Context.cast(value)

        def callee(session):
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
            prepared_query = session.prepare(query)

            session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                {"$queryId": str(key), "$queryContext": value.json()},
                commit_tx=True,
            )

        return self.pool.retry_operation_sync(callee)

    @threadsafe_method
    def __getitem__(self, key: str) -> Context:
        def callee(session):
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
            prepared_query = session.prepare(query)

            result_sets = session.transaction(ydb.SerializableReadWrite()).execute(
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

        return self.pool.retry_operation_sync(callee)

    @threadsafe_method
    def __delitem__(self, key: str) -> None:
        def callee(session):
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
            prepared_query = session.prepare(query)

            session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                {"$queryId": str(key)},
                commit_tx=True,
            )

        return self.pool.retry_operation_sync(callee)

    @threadsafe_method
    def __contains__(self, key: str) -> bool:
        def callee(session):
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
            prepared_query = session.prepare(query)

            result_sets = session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                {
                    "$queryId": str(key),
                },
                commit_tx=True,
            )
            return len(result_sets[0].rows) > 0

        return self.pool.retry_operation_sync(callee)

    @threadsafe_method
    def __len__(self) -> int:
        def callee(session):
            query = """
                PRAGMA TablePathPrefix("{}");

                SELECT
                    COUNT(*) as cnt
                FROM {}
                """.format(
                self.database, self.table_name
            )
            prepared_query = session.prepare(query)

            result_sets = session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                commit_tx=True,
            )
            return result_sets[0].rows[0].cnt

        return self.pool.retry_operation_sync(callee)

    @threadsafe_method
    def clear(self) -> None:
        def callee(session):
            query = """
                PRAGMA TablePathPrefix("{}");
                DECLARE $queryId AS Utf8;

                DELETE
                FROM {}
                ;
                """.format(
                self.database, self.table_name
            )
            prepared_query = session.prepare(query)

            session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                {},
                commit_tx=True,
            )

        return self.pool.retry_operation_sync(callee)

    def _is_table_exists(self, pool, path, table_name):
        try:

            def callee(session):
                session.describe_table(os.path.join(path, table_name))

            pool.retry_operation_sync(callee)
            return True
        except ydb.SchemeError:
            return False

    def _create_table(self, pool, path, table_name):
        def callee(session):
            session.create_table(
                "/".join([path, table_name]),
                ydb.TableDescription()
                .with_column(ydb.Column("id", ydb.OptionalType(ydb.PrimitiveType.Utf8)))
                .with_column(ydb.Column("context", ydb.OptionalType(ydb.PrimitiveType.Json)))
                .with_primary_key("id"),
            )

        return pool.retry_operation_sync(callee)
