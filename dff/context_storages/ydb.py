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
import pickle
import time
from typing import Hashable, Union, List, Dict, Tuple, Optional, Any
from urllib.parse import urlsplit

from dff.script import Context

from .database import DBContextStorage, auto_stringify_hashable_key
from .protocol import get_protocol_install_suggestion
from .update_scheme import UpdateScheme, ExtraFields, FieldRule, DictField, ListField, ValueField

try:
    from ydb import SerializableReadWrite, SchemeError, TableDescription, Column, OptionalType, PrimitiveType
    from ydb.aio import Driver, SessionPool

    ydb_available = True
except ImportError:
    ydb_available = False


class YDBContextStorage(DBContextStorage):
    """
    Version of the :py:class:`.DBContextStorage` for YDB.

    :param path: Standard sqlalchemy URI string. One of `grpc` or `grpcs` can be chosen as a protocol.
        Example: `grpc://localhost:2134/local`.
    :param table_name: The name of the table to use.
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
        list_fields = [
            field for field, field_props in dict(self.update_scheme).items() if isinstance(field_props, ListField)
        ]
        dict_fields = [
            field for field, field_props in dict(self.update_scheme).items() if isinstance(field_props, DictField)
        ]
        self.driver, self.pool = asyncio.run(
            _init_drive(
                timeout, self.endpoint, self.database, table_name_prefix, self.update_scheme, list_fields, dict_fields
            )
        )

    def set_update_scheme(self, scheme: UpdateScheme):
        super().set_update_scheme(scheme)
        self.update_scheme.id.on_write = FieldRule.UPDATE_ONCE
        self.update_scheme.ext_id.on_write = FieldRule.UPDATE_ONCE
        self.update_scheme.created_at.on_write = FieldRule.UPDATE_ONCE
        self.update_scheme.updated_at.on_write = FieldRule.UPDATE

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
        fields, _ = await self._read_keys(key)
        value_hash = self.hash_storage.get(key, None)
        await self.update_scheme.write_context(value, value_hash, fields, self._write_ctx, key)

    @auto_stringify_hashable_key()
    async def del_item_async(self, key: Union[Hashable, str]):
        async def callee(session):
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                DECLARE $ext_id AS Utf8;
                DECLARE $created_at AS Uint64;
                DECLARE $updated_at AS Uint64;
                INSERT INTO {self.table_prefix}_{self._CONTEXTS} ({self.update_scheme.id.name}, {self.update_scheme.ext_id.name}, {self.update_scheme.created_at.name}, {self.update_scheme.updated_at.name})
                VALUES (NULL, $ext_id, DateTime::FromMicroseconds($created_at), DateTime::FromMicroseconds($updated_at));
                """  # noqa 501

            now = time.time_ns() // 1000
            await (session.transaction(SerializableReadWrite())).execute(
                await session.prepare(query),
                {"$ext_id": key, "$created_at": now, "$updated_at": now},
                commit_tx=True,
            )

        return await self.pool.retry_operation(callee)

    @auto_stringify_hashable_key()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        async def callee(session):
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                DECLARE $externalId AS Utf8;
                SELECT {self.update_scheme.id.name} as int_id, {self.update_scheme.created_at.name}
                FROM {self.table_prefix}_{self._CONTEXTS}
                WHERE {self.update_scheme.ext_id.name} = $externalId
                ORDER BY {self.update_scheme.created_at.name} DESC
                LIMIT 1;
                """

            result_sets = await (session.transaction(SerializableReadWrite())).execute(
                await session.prepare(query),
                {"$externalId": key},
                commit_tx=True,
            )
            return result_sets[0].rows[0].int_id is not None if len(result_sets[0].rows) > 0 else False

        return await self.pool.retry_operation(callee)

    async def len_async(self) -> int:
        async def callee(session):
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                SELECT COUNT(DISTINCT {self.update_scheme.ext_id.name}) as cnt
                FROM {self.table_prefix}_{self._CONTEXTS}
                WHERE {self.update_scheme.id.name} IS NOT NULL;
                """

            result_sets = await (session.transaction(SerializableReadWrite())).execute(
                await session.prepare(query),
                commit_tx=True,
            )
            return result_sets[0].rows[0].cnt if len(result_sets[0].rows) > 0 else 0

        return await self.pool.retry_operation(callee)

    async def clear_async(self):
        async def ids_callee(session):
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                SELECT DISTINCT {self.update_scheme.ext_id.name} as ext_id
                FROM {self.table_prefix}_{self._CONTEXTS};
                """

            result_sets = await (session.transaction(SerializableReadWrite())).execute(
                await session.prepare(query),
                commit_tx=True,
            )
            return result_sets[0].rows if len(result_sets[0].rows) > 0 else None

        async def callee(session):
            ids = await ids_callee(session)
            if ids is None:
                return
            else:
                ids = list(ident["ext_id"] for ident in ids)

            external_ids = [f"$ext_id_{i}" for i in range(len(ids))]
            values = [
                f"(NULL, {i}, DateTime::FromMicroseconds($created_at), DateTime::FromMicroseconds($updated_at))"
                for i in external_ids
            ]
            declarations = "\n".join(f"DECLARE {i} AS Utf8;" for i in external_ids)

            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                {declarations}
                DECLARE $created_at AS Uint64;
                DECLARE $updated_at AS Uint64;
                INSERT INTO {self.table_prefix}_{self._CONTEXTS} ({self.update_scheme.id.name}, {self.update_scheme.ext_id.name}, {self.update_scheme.created_at.name}, {self.update_scheme.updated_at.name})
                VALUES {', '.join(values)};
                """  # noqa 501

            now = time.time_ns() // 1000
            await (session.transaction(SerializableReadWrite())).execute(
                await session.prepare(query),
                {**{word: eid for word, eid in zip(external_ids, ids)}, "$created_at": now, "$updated_at": now},
                commit_tx=True,
            )

        return await self.pool.retry_operation(callee)

    async def _read_keys(self, ext_id: str) -> Tuple[Dict[str, List[str]], Optional[str]]:
        async def latest_id_callee(session):
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                DECLARE $externalId AS Utf8;
                SELECT {self.update_scheme.id.name} as int_id, {self.update_scheme.created_at.name}
                FROM {self.table_prefix}_{self._CONTEXTS}
                WHERE {self.update_scheme.ext_id.name} = $externalId
                ORDER BY {self.update_scheme.created_at.name} DESC
                LIMIT 1;
                """

            result_sets = await (session.transaction(SerializableReadWrite())).execute(
                await session.prepare(query),
                {"$externalId": ext_id},
                commit_tx=True,
            )
            return result_sets[0].rows[0].int_id if len(result_sets[0].rows) > 0 else None

        async def keys_callee(session):
            key_dict = dict()
            int_id = await latest_id_callee(session)
            if int_id is None:
                return key_dict, None

            for table in [
                field
                for field, field_props in dict(self.update_scheme).items()
                if not isinstance(field_props, ValueField)
            ]:
                query = f"""
                    PRAGMA TablePathPrefix("{self.database}");
                    DECLARE $internalId AS Utf8;
                    SELECT {self._KEY_FIELD}
                    FROM {self.table_prefix}_{table}
                    WHERE id = $internalId;
                    """

                result_sets = await (session.transaction(SerializableReadWrite())).execute(
                    await session.prepare(query),
                    {"$internalId": int_id},
                    commit_tx=True,
                )

                if len(result_sets[0].rows) > 0:
                    key_dict[table] = [row[self._KEY_FIELD] for row in result_sets[0].rows]

            return key_dict, int_id

        return await self.pool.retry_operation(keys_callee)

    async def _read_ctx(self, subscript: Dict[str, Union[bool, Dict[Hashable, bool]]], int_id: str, _: str) -> Dict:
        async def callee(session):
            result_dict = dict()
            for field in [field for field, value in subscript.items() if isinstance(value, dict) and len(value) > 0]:
                keys = [f'"{key}"' for key, value in subscript[field].items() if value]
                query = f"""
                    PRAGMA TablePathPrefix("{self.database}");
                    DECLARE $int_id AS Utf8;
                    SELECT {self._KEY_FIELD}, {self._VALUE_FIELD}
                    FROM {self.table_prefix}_{field}
                    WHERE {self.update_scheme.id.name} = $int_id AND ListHas(AsList({', '.join(keys)}), {self._KEY_FIELD});
                    """  # noqa E501

                result_sets = await (session.transaction(SerializableReadWrite())).execute(
                    await session.prepare(query),
                    {"$int_id": int_id},
                    commit_tx=True,
                )

                if len(result_sets[0].rows) > 0:
                    for key, value in {
                        row[self._KEY_FIELD]: row[self._VALUE_FIELD] for row in result_sets[0].rows
                    }.items():
                        if value is not None:
                            if field not in result_dict:
                                result_dict[field] = dict()
                            result_dict[field][key] = pickle.loads(value)

            columns = [key for key, value in subscript.items() if isinstance(value, bool) and value]
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                DECLARE $int_id AS Utf8;
                SELECT {', '.join(columns)}
                FROM {self.table_prefix}_{self._CONTEXTS}
                WHERE {self.update_scheme.id.name} = $int_id;
                """

            result_sets = await (session.transaction(SerializableReadWrite())).execute(
                await session.prepare(query),
                {"$int_id": int_id},
                commit_tx=True,
            )

            if len(result_sets[0].rows) > 0:
                for key, value in {column: result_sets[0].rows[0][column] for column in columns}.items():
                    if value is not None:
                        result_dict[key] = value
            return result_dict

        return await self.pool.retry_operation(callee)

    async def _write_ctx(self, data: Dict[str, Any], int_id: str, _: str):
        async def callee(session):
            for field, storage in {k: v for k, v in data.items() if isinstance(v, dict)}.items():
                if len(storage.items()) > 0:
                    key_type = "Utf8" if isinstance(getattr(self.update_scheme, field), DictField) else "Uint32"
                    declares_ids = "\n".join(f"DECLARE $int_id_{i} AS Utf8;" for i in range(len(storage)))
                    declares_keys = "\n".join(f"DECLARE $key_{i} AS {key_type};" for i in range(len(storage)))
                    declares_values = "\n".join(f"DECLARE $value_{i} AS String;" for i in range(len(storage)))
                    values_all = ", ".join(f"($int_id_{i}, $key_{i}, $value_{i})" for i in range(len(storage)))
                    query = f"""
                        PRAGMA TablePathPrefix("{self.database}");
                        {declares_ids}
                        {declares_keys}
                        {declares_values}
                        UPSERT INTO {self.table_prefix}_{field} ({self.update_scheme.id.name}, {self._KEY_FIELD}, {self._VALUE_FIELD})
                        VALUES {values_all};
                        """  # noqa E501

                    values_ids = {f"$int_id_{i}": int_id for i, _ in enumerate(storage)}
                    values_keys = {f"$key_{i}": key for i, key in enumerate(storage.keys())}
                    values_values = {f"$value_{i}": pickle.dumps(value) for i, value in enumerate(storage.values())}
                    await (session.transaction(SerializableReadWrite())).execute(
                        await session.prepare(query),
                        {**values_ids, **values_keys, **values_values},
                        commit_tx=True,
                    )
            values = {**{k: v for k, v in data.items() if not isinstance(v, dict)}, self.update_scheme.id.name: int_id}
            if len(values.items()) > 0:
                declarations = list()
                inserted = list()
                for key in values.keys():
                    if key in (self.update_scheme.id.name, self.update_scheme.ext_id.name):
                        declarations += [f"DECLARE ${key} AS Utf8;"]
                        inserted += [f"${key}"]
                    elif key in (self.update_scheme.created_at.name, self.update_scheme.updated_at.name):
                        declarations += [f"DECLARE ${key} AS Uint64;"]
                        inserted += [f"DateTime::FromMicroseconds(${key})"]
                        values[key] = values[key] // 1000
                    else:
                        raise RuntimeError(
                            f"Pair ({key}, {values[key]}) can't be written to table: no columns defined for them!"
                        )
                declarations = "\n".join(declarations)

                query = f"""
                    PRAGMA TablePathPrefix("{self.database}");
                    {declarations}
                    UPSERT INTO {self.table_prefix}_{self._CONTEXTS} ({', '.join(key for key in values.keys())})
                    VALUES ({', '.join(inserted)});
                    """
                await (session.transaction(SerializableReadWrite())).execute(
                    await session.prepare(query),
                    {f"${key}": value for key, value in values.items()},
                    commit_tx=True,
                )

        return await self.pool.retry_operation(callee)


async def _init_drive(
    timeout: int,
    endpoint: str,
    database: str,
    table_name_prefix: str,
    scheme: UpdateScheme,
    list_fields: List[str],
    dict_fields: List[str],
):
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
            .with_column(Column(ExtraFields.id, PrimitiveType.Utf8))
            .with_column(Column(YDBContextStorage._KEY_FIELD, PrimitiveType.Uint32))
            .with_column(Column(YDBContextStorage._VALUE_FIELD, OptionalType(PrimitiveType.String)))
            .with_primary_keys(ExtraFields.id, YDBContextStorage._KEY_FIELD),
        )

    return await pool.retry_operation(callee)


async def _create_dict_table(pool, path, table_name):
    async def callee(session):
        await session.create_table(
            "/".join([path, table_name]),
            TableDescription()
            .with_column(Column(ExtraFields.id, PrimitiveType.Utf8))
            .with_column(Column(YDBContextStorage._KEY_FIELD, PrimitiveType.Utf8))
            .with_column(Column(YDBContextStorage._VALUE_FIELD, OptionalType(PrimitiveType.String)))
            .with_primary_keys(ExtraFields.id, YDBContextStorage._KEY_FIELD),
        )

    return await pool.retry_operation(callee)


async def _create_contexts_table(pool, path, table_name, update_scheme):
    async def callee(session):
        table = (
            TableDescription()
            .with_column(Column(ExtraFields.id, OptionalType(PrimitiveType.Utf8)))
            .with_column(Column(ExtraFields.ext_id, OptionalType(PrimitiveType.Utf8)))
            .with_column(Column(ExtraFields.created_at, OptionalType(PrimitiveType.Timestamp)))
            .with_column(Column(ExtraFields.updated_at, OptionalType(PrimitiveType.Timestamp)))
            .with_primary_key(ExtraFields.id)
        )

        await session.create_table("/".join([path, table_name]), table)

        for field, field_props in dict(update_scheme).items():
            if isinstance(field_props, ValueField) and field not in [c.name for c in table.columns]:
                if field_props.on_read != FieldRule.IGNORE or field_props.on_write != FieldRule.IGNORE:
                    raise RuntimeError(
                        f"Value field `{field}` is not ignored in the scheme, yet no columns are created for it!"
                    )

    return await pool.retry_operation(callee)
