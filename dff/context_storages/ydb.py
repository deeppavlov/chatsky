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
from typing import Hashable, Union, List, Dict, Tuple, Optional
from urllib.parse import urlsplit

from dff.script import Context

from .database import DBContextStorage, auto_stringify_hashable_key
from .protocol import get_protocol_install_suggestion
from .update_scheme import UpdateScheme, UpdateSchemeBuilder, ExtraFields, FieldRule, FieldType

try:
    from ydb import SerializableReadWrite, SchemeError, TableDescription, Column, OptionalType, PrimitiveType
    from ydb.aio import Driver, SessionPool

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
    :type table_name: str
    """

    _CONTEXTS = "contexts"
    _KEY_FIELD = "key"
    _VALUE_FIELD = "value"

    def __init__(self, path: str, table_name_prefix: str = "dff_table", timeout=5):
        DBContextStorage.__init__(self, path)
        protocol, netloc, self.database, _, _ = urlsplit(path)
        self.endpoint = "{}://{}".format(protocol, netloc)
        if not ydb_available:
            install_suggestion = get_protocol_install_suggestion("grpc")
            raise ImportError("`ydb` package is missing.\n" + install_suggestion)

        self.table_prefix = table_name_prefix
        list_fields = [field for field in UpdateScheme.ALL_FIELDS if self.update_scheme.fields[field]["type"] == FieldType.LIST]
        dict_fields = [field for field in UpdateScheme.ALL_FIELDS if self.update_scheme.fields[field]["type"] == FieldType.DICT]
        self.driver, self.pool = asyncio.run(_init_drive(timeout, self.endpoint, self.database, table_name_prefix, self.update_scheme, list_fields, dict_fields))

    def set_update_scheme(self, scheme: Union[UpdateScheme, UpdateSchemeBuilder]):
        super().set_update_scheme(scheme)
        self.update_scheme.fields[ExtraFields.IDENTITY_FIELD].update(write=FieldRule.UPDATE_ONCE)
        self.update_scheme.fields[ExtraFields.EXTERNAL_FIELD].update(write=FieldRule.UPDATE_ONCE)

    @auto_stringify_hashable_key()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        fields, int_id = await self._read_keys(key)
        if int_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.update_scheme.read_context(fields, self._read_ctx, key, int_id)
        self.hash_storage[key] = hashes
        return context

    @auto_stringify_hashable_key()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
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

            await (session.transaction(SerializableReadWrite())).execute(
                prepared_query,
                {"$queryId": str(key), "$queryContext": value.json()},
                commit_tx=True,
            )

        return await self.pool.retry_operation(callee)

    @auto_stringify_hashable_key()
    async def del_item_async(self, key: Union[Hashable, str]):
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

            await (session.transaction(SerializableReadWrite())).execute(
                prepared_query,
                {"$queryId": str(key)},
                commit_tx=True,
            )

        return await self.pool.retry_operation(callee)

    @auto_stringify_hashable_key()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
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

            result_sets = await (session.transaction(SerializableReadWrite())).execute(
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

            result_sets = await (session.transaction(SerializableReadWrite())).execute(
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

            await (session.transaction(SerializableReadWrite())).execute(
                prepared_query,
                {},
                commit_tx=True,
            )

        return await self.pool.retry_operation(callee)

    async def _read_keys(self, ext_id: str) -> Tuple[Dict[str, List[str]], Optional[str]]:
        async def latest_id_callee(session):
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                DECLARE $externalId AS Utf8;
                SELECT {ExtraFields.IDENTITY_FIELD}
                FROM {self.table_prefix}_{self._CONTEXTS}
                WHERE {ExtraFields.EXTERNAL_FIELD} = $externalId;
                """

            result_sets = await (session.transaction(SerializableReadWrite())).execute(
                await session.prepare(query),
                {"$externalId": ext_id},
                commit_tx=True,
            )
            if result_sets[0].rows:
                return Context.cast(result_sets[0].rows[0][ExtraFields.EXTERNAL_FIELD])
            else:
                raise None

        async def keys_callee(session):
            int_id = latest_id_callee(session)

            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                DECLARE $internalId AS Utf8;
                SELECT
                    id,
                    context
                FROM {self.table_name}
                WHERE id = $internalId;
                """

            result_sets = await (session.transaction(SerializableReadWrite())).execute(
                await session.prepare(query),
                {"$internalId": ext_id},
                commit_tx=True,
            )
            if result_sets[0].rows:
                return Context.cast(result_sets[0].rows[0].context)
            else:
                raise KeyError

        return await self.pool.retry_operation(keys_callee)

    async def _read_ctx(self, outlook: Dict[str, Union[bool, Dict[Hashable, bool]]], int_id: str, _: str) -> Dict:
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

            result_sets = await (session.transaction(SerializableReadWrite())).execute(
                prepared_query,
                {
                    "$queryId": int_id,
                },
                commit_tx=True,
            )
            if result_sets[0].rows:
                return Context.cast(result_sets[0].rows[0].context)
            else:
                raise KeyError

        return await self.pool.retry_operation(callee)


async def _init_drive(timeout: int, endpoint: str, database: str, table_name_prefix: str, scheme: UpdateScheme, list_fields: List[str], dict_fields: List[str]):
    driver = Driver(endpoint=endpoint, database=database)
    await driver.wait(fail_fast=True, timeout=timeout)

    pool = SessionPool(driver, size=10)

    for field in list_fields:
        table_name = f"{table_name_prefix}_{field}"
        if not await _is_table_exists(pool, database, table_name):
            await _create_list_table(pool, database, table_name)

    for field in dict_fields:
        table_name = f"{table_name_prefix}_{field}"
        if not await _is_table_exists(pool, database, table_name):
            await _create_dict_table(pool, database, table_name)

    table_name = f"{table_name_prefix}_{YDBContextStorage._CONTEXTS}"
    if not await _is_table_exists(pool, database, table_name):
        await _create_contexts_table(pool, database, table_name, scheme)
    return driver, pool


async def _is_table_exists(pool, path, table_name) -> bool:
    try:

        async def callee(session):
            await session.describe_table(os.path.join(path, table_name))

        await pool.retry_operation(callee)
        return True
    except SchemeError:
        return False


async def _create_list_table(pool, path, table_name):
    async def callee(session):
        await session.create_table(
            "/".join([path, table_name]),
            TableDescription()
            .with_column(Column(ExtraFields.IDENTITY_FIELD, OptionalType(PrimitiveType.Utf8)))
            .with_column(Column(YDBContextStorage._KEY_FIELD, OptionalType(PrimitiveType.Uint32)))
            .with_column(Column(YDBContextStorage._VALUE_FIELD, OptionalType(PrimitiveType.Yson)))
            # TODO: nullable, indexes, unique.
        )

    return await pool.retry_operation(callee)


async def _create_dict_table(pool, path, table_name):
    async def callee(session):
        await session.create_table(
            "/".join([path, table_name]),
            TableDescription()
            .with_column(Column(ExtraFields.IDENTITY_FIELD, OptionalType(PrimitiveType.Utf8)))
            .with_column(Column(YDBContextStorage._KEY_FIELD, OptionalType(PrimitiveType.Utf8)))
            .with_column(Column(YDBContextStorage._VALUE_FIELD, OptionalType(PrimitiveType.Yson)))
            # TODO: nullable, indexes, unique.
        )

    return await pool.retry_operation(callee)


async def _create_contexts_table(pool, path, table_name, update_scheme):
    async def callee(session):
        table = TableDescription() \
            .with_column(Column(ExtraFields.IDENTITY_FIELD, OptionalType(PrimitiveType.Utf8))) \
            .with_column(Column(ExtraFields.EXTERNAL_FIELD, OptionalType(PrimitiveType.Utf8))) \
            .with_column(Column(ExtraFields.CREATED_AT_FIELD, OptionalType(PrimitiveType.Datetime))) \
            .with_column(Column(ExtraFields.UPDATED_AT_FIELD, OptionalType(PrimitiveType.Datetime)))
        # TODO: nullable, indexes, unique, defaults.

        await session.create_table(
            "/".join([path, table_name]),
            table
        )

        for field in UpdateScheme.ALL_FIELDS:
            if update_scheme.fields[field]["type"] == FieldType.VALUE and field not in [c.name for c in table.columns]:
                if update_scheme.fields[field]["read"] != FieldRule.IGNORE or update_scheme.fields[field]["write"] != FieldRule.IGNORE:
                    raise RuntimeError(f"Value field `{field}` is not ignored in the scheme, yet no columns are created for it!")

    return await pool.retry_operation(callee)
