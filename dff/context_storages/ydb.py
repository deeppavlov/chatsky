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
from typing import Hashable, Union, List, Dict, Optional
from urllib.parse import urlsplit

from dff.script import Context

from .database import DBContextStorage, cast_key_to_string
from .protocol import get_protocol_install_suggestion
from .context_schema import (
    ContextSchema,
    ExtraFields,
    FieldDescriptor,
    FrozenValueSchemaField,
    SchemaFieldWritePolicy,
    SchemaFieldReadPolicy,
    DictSchemaField,
    ListSchemaField,
    ValueSchemaField,
)

try:
    from ydb import (
        SerializableReadWrite,
        SchemeError,
        TableDescription,
        Column,
        OptionalType,
        PrimitiveType,
        TableIndex,
    )
    from ydb.aio import Driver, SessionPool
    from ydb.issues import PreconditionFailed

    ydb_available = True
except ImportError:
    ydb_available = False


class YDBContextStorage(DBContextStorage):
    """
    Version of the :py:class:`.DBContextStorage` for YDB.

    Context value fields are stored in table `contexts`.
    Columns of the table are: active_ctx, primary_id, storage_key, created_at and updated_at.

    Context dictionary fields are stored in tables `TABLE_NAME_PREFIX_FIELD`.
    Columns of the tables are: primary_id, key, value, created_at and updated_at,
    where key contains nested dict key and value contains nested dict value.

    Context reading is done with one query to each table.
    Context reading is done with multiple queries to each table, one for each nested key.

    :param path: Standard sqlalchemy URI string. One of `grpc` or `grpcs` can be chosen as a protocol.
        Example: `grpc://localhost:2134/local`.
        NB! Do not forget to provide credentials in environmental variables
        or set `YDB_ANONYMOUS_CREDENTIALS` variable to `1`!
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
            field
            for field, field_props in dict(self.context_schema).items()
            if isinstance(field_props, ListSchemaField)
        ]
        dict_fields = [
            field
            for field, field_props in dict(self.context_schema).items()
            if isinstance(field_props, DictSchemaField)
        ]
        self.driver, self.pool = asyncio.run(
            _init_drive(
                timeout, self.endpoint, self.database, table_name_prefix, self.context_schema, list_fields, dict_fields
            )
        )

    def set_context_schema(self, scheme: ContextSchema):
        super().set_context_schema(scheme)
        params = {
            **self.context_schema.dict(),
            "active_ctx": FrozenValueSchemaField(name=ExtraFields.active_ctx, on_write=SchemaFieldWritePolicy.IGNORE),
            "created_at": ValueSchemaField(name=ExtraFields.created_at, on_write=SchemaFieldWritePolicy.IGNORE),
            "updated_at": ValueSchemaField(name=ExtraFields.updated_at, on_write=SchemaFieldWritePolicy.IGNORE),
        }
        self.context_schema = ContextSchema(**params)

    @cast_key_to_string()
    async def get_item_async(self, key: str) -> Context:
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.context_schema.read_context(self._read_ctx, key, primary_id)
        self.hash_storage[key] = hashes
        return context

    @cast_key_to_string()
    async def set_item_async(self, key: str, value: Context):
        primary_id = await self._get_last_ctx(key)
        value_hash = self.hash_storage.get(key)
        await self.context_schema.write_context(value, value_hash, self._write_ctx_val, key, primary_id, 10000)

    @cast_key_to_string()
    async def del_item_async(self, key: str):
        async def callee(session):
            query = f"""
PRAGMA TablePathPrefix("{self.database}");
DECLARE ${ExtraFields.storage_key.value} AS Utf8;
UPDATE {self.table_prefix}_{self._CONTEXTS} SET {ExtraFields.active_ctx.value}=False
WHERE {ExtraFields.storage_key.value} == ${ExtraFields.storage_key.value};
"""

            await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query),
                {f"${ExtraFields.storage_key.value}": key},
                commit_tx=True,
            )

        self.hash_storage[key] = None
        return await self.pool.retry_operation(callee)

    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        return await self._get_last_ctx(key) is not None

    async def len_async(self) -> int:
        async def callee(session):
            query = f"""
PRAGMA TablePathPrefix("{self.database}");
SELECT COUNT(DISTINCT {ExtraFields.storage_key.value}) as cnt
FROM {self.table_prefix}_{self._CONTEXTS}
WHERE {ExtraFields.active_ctx.value} == True;
"""

            result_sets = await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query),
                commit_tx=True,
            )
            return result_sets[0].rows[0].cnt if len(result_sets[0].rows) > 0 else 0

        return await self.pool.retry_operation(callee)

    async def clear_async(self):
        async def callee(session):
            query = f"""
PRAGMA TablePathPrefix("{self.database}");
UPDATE {self.table_prefix}_{self._CONTEXTS} SET {ExtraFields.active_ctx.value}=False;
"""

            await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query),
                commit_tx=True,
            )

        self.hash_storage = {key: None for key, _ in self.hash_storage.items()}
        return await self.pool.retry_operation(callee)

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        async def callee(session):
            query = f"""
PRAGMA TablePathPrefix("{self.database}");
DECLARE ${ExtraFields.storage_key.value} AS Utf8;
SELECT {ExtraFields.primary_id.value}
FROM {self.table_prefix}_{self._CONTEXTS}
WHERE {ExtraFields.storage_key.value} == ${ExtraFields.storage_key.value} AND {ExtraFields.active_ctx.value} == True
LIMIT 1;
"""

            result_sets = await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query),
                {f"${ExtraFields.storage_key.value}": storage_key},
                commit_tx=True,
            )
            return result_sets[0].rows[0][ExtraFields.primary_id.value] if len(result_sets[0].rows) > 0 else None

        return await self.pool.retry_operation(callee)

    async def _read_ctx(self, subscript: Dict[str, Union[bool, int, List[Hashable]]], primary_id: str) -> Dict:
        async def callee(session):
            result_dict, values_slice = dict(), list()

            for field, value in subscript.items():
                if isinstance(value, bool) and value:
                    values_slice += [field]
                else:
                    query = f"""
PRAGMA TablePathPrefix("{self.database}");
DECLARE ${ExtraFields.primary_id.value} AS Utf8;
SELECT {self._KEY_FIELD}, {self._VALUE_FIELD}
FROM {self.table_prefix}_{field}
WHERE {ExtraFields.primary_id.value} = ${ExtraFields.primary_id.value}
"""

                    if isinstance(value, int):
                        if value > 0:
                            query += f"""
ORDER BY {self._KEY_FIELD} ASC
LIMIT {value}
"""
                        else:
                            query += f"""
ORDER BY {self._KEY_FIELD} DESC
LIMIT {-value}
"""
                    elif isinstance(value, list):
                        keys = [f'"{key}"' for key in value]
                        query += f" AND ListHas(AsList({', '.join(keys)}), {self._KEY_FIELD})\nLIMIT 1001"
                    else:
                        query += "\nLIMIT 1001"

                    final_offset = 0
                    result_sets = None

                    while result_sets is None or result_sets[0].truncated:
                        final_query = f"{query} OFFSET {final_offset};"
                        result_sets = await session.transaction(SerializableReadWrite()).execute(
                            await session.prepare(final_query),
                            {f"${ExtraFields.primary_id.value}": primary_id},
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

                        final_offset += 1000

            columns = [key for key in values_slice]
            query = f"""
PRAGMA TablePathPrefix("{self.database}");
DECLARE ${ExtraFields.primary_id.value} AS Utf8;
SELECT {', '.join(columns)}
FROM {self.table_prefix}_{self._CONTEXTS}
WHERE {ExtraFields.primary_id.value} = ${ExtraFields.primary_id.value};
"""

            result_sets = await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query),
                {f"${ExtraFields.primary_id.value}": primary_id},
                commit_tx=True,
            )

            if len(result_sets[0].rows) > 0:
                for key, value in {column: result_sets[0].rows[0][column] for column in columns}.items():
                    if value is not None:
                        result_dict[key] = value
            return result_dict

        return await self.pool.retry_operation(callee)

    async def _write_ctx_val(self, field: Optional[str], payload: FieldDescriptor, nested: bool, primary_id: str):
        async def callee(session):
            if nested and len(payload[0]) > 0:
                data, enforce = payload

                if enforce:
                    key_type = "Utf8" if isinstance(getattr(self.context_schema, field), DictSchemaField) else "Uint32"
                    declares_keys = "\n".join(f"DECLARE $key_{i} AS {key_type};" for i in range(len(data)))
                    declares_values = "\n".join(f"DECLARE $value_{i} AS String;" for i in range(len(data)))
                    two_current_times = "CurrentUtcDatetime(), CurrentUtcDatetime()"
                    values_all = ", ".join(
                        f"(${ExtraFields.primary_id.value}, {two_current_times}, $key_{i}, $value_{i})"
                        for i in range(len(data))
                    )

                    default_times = f"{ExtraFields.created_at.value}, {ExtraFields.updated_at.value}"
                    special_values = f"{self._KEY_FIELD}, {self._VALUE_FIELD}"
                    query = f"""
PRAGMA TablePathPrefix("{self.database}");
DECLARE ${ExtraFields.primary_id.value} AS Utf8;
{declares_keys}
{declares_values}
UPSERT INTO {self.table_prefix}_{field} ({ExtraFields.primary_id.value}, {default_times}, {special_values})
VALUES {values_all};
"""

                    values_keys = {f"$key_{i}": key for i, key in enumerate(data.keys())}
                    values_values = {f"$value_{i}": pickle.dumps(value) for i, value in enumerate(data.values())}
                    await session.transaction(SerializableReadWrite()).execute(
                        await session.prepare(query),
                        {f"${ExtraFields.primary_id.value}": primary_id, **values_keys, **values_values},
                        commit_tx=True,
                    )

                else:
                    for (
                        key,
                        value,
                    ) in (
                        data.items()
                    ):  # We've got no other choice: othervise if some fields fail to be `INSERT`ed other will fail too
                        key_type = (
                            "Utf8" if isinstance(getattr(self.context_schema, field), DictSchemaField) else "Uint32"
                        )
                        keyword = "UPSERT" if enforce else "INSERT"
                        default_times = f"{ExtraFields.created_at.value}, {ExtraFields.updated_at.value}"
                        special_values = f"{self._KEY_FIELD}, {self._VALUE_FIELD}"
                        query = f"""
PRAGMA TablePathPrefix("{self.database}");
DECLARE ${ExtraFields.primary_id.value} AS Utf8;
DECLARE $key_{field} AS {key_type};
DECLARE $value_{field} AS String;
{keyword} INTO {self.table_prefix}_{field} ({ExtraFields.primary_id.value}, {default_times}, {special_values})
VALUES (${ExtraFields.primary_id.value}, CurrentUtcDatetime(), CurrentUtcDatetime(), $key_{field}, $value_{field});
"""

                        try:
                            await session.transaction(SerializableReadWrite()).execute(
                                await session.prepare(query),
                                {
                                    f"${ExtraFields.primary_id.value}": primary_id,
                                    f"$key_{field}": key,
                                    f"$value_{field}": pickle.dumps(value),
                                },
                                commit_tx=True,
                            )
                        except PreconditionFailed:
                            if not enforce:
                                pass  # That would mean that `INSERT` query failed successfully 👍

            elif not nested and len(payload) > 0:
                values = {key: data for key, (data, _) in payload.items()}
                enforces = [enforced for _, enforced in payload.values()]
                stored = (await self._get_last_ctx(values[ExtraFields.storage_key.value])) is not None

                declarations = list()
                inserted = list()
                inset = list()
                for idx, key in enumerate(values.keys()):
                    if key in (ExtraFields.primary_id.value, ExtraFields.storage_key.value):
                        declarations += [f"DECLARE ${key} AS Utf8;"]
                        inserted += [f"${key}"]
                        inset += [f"{key}=${key}"] if enforces[idx] else []
                    elif key == ExtraFields.active_ctx.value:
                        declarations += [f"DECLARE ${key} AS Bool;"]
                        inserted += [f"${key}"]
                        inset += [f"{key}=${key}"] if enforces[idx] else []
                    else:
                        raise RuntimeError(
                            f"Pair ({key}, {values[key]}) can't be written to table: no columns defined for them!"
                        )
                declarations = "\n".join(declarations)

                if stored:
                    query = f"""
PRAGMA TablePathPrefix("{self.database}");
DECLARE ${ExtraFields.primary_id.value} AS Utf8;
{declarations}
UPDATE {self.table_prefix}_{self._CONTEXTS} SET {', '.join(inset)}, {ExtraFields.active_ctx.value}=True
WHERE {ExtraFields.primary_id.value} = ${ExtraFields.primary_id.value};
"""
                else:
                    prefix_columns = f"{ExtraFields.primary_id.value}, {ExtraFields.active_ctx.value}"
                    all_keys = ", ".join(key for key in values.keys())
                    query = f"""
PRAGMA TablePathPrefix("{self.database}");
DECLARE ${ExtraFields.primary_id.value} AS Utf8;
{declarations}
UPSERT INTO {self.table_prefix}_{self._CONTEXTS} ({prefix_columns}, {all_keys})
VALUES (${ExtraFields.primary_id.value}, True, {', '.join(inserted)});
"""

                await session.transaction(SerializableReadWrite()).execute(
                    await session.prepare(query),
                    {
                        **{f"${key}": value for key, value in values.items()},
                        f"${ExtraFields.primary_id.value}": primary_id,
                    },
                    commit_tx=True,
                )

        return await self.pool.retry_operation(callee)


async def _init_drive(
    timeout: int,
    endpoint: str,
    database: str,
    table_name_prefix: str,
    scheme: ContextSchema,
    list_fields: List[str],
    dict_fields: List[str],
):
    driver = Driver(endpoint=endpoint, database=database)
    client_settings = driver.table_client._table_client_settings.with_allow_truncated_result(True)
    driver.table_client._table_client_settings = client_settings
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
            .with_column(Column(ExtraFields.primary_id.value, PrimitiveType.Utf8))
            .with_column(Column(ExtraFields.created_at.value, OptionalType(PrimitiveType.Timestamp)))
            .with_column(Column(ExtraFields.updated_at.value, OptionalType(PrimitiveType.Timestamp)))
            .with_column(Column(YDBContextStorage._KEY_FIELD, PrimitiveType.Uint32))
            .with_column(Column(YDBContextStorage._VALUE_FIELD, OptionalType(PrimitiveType.String)))
            .with_index(TableIndex(f"{table_name}_list_index").with_index_columns(ExtraFields.primary_id.value))
            .with_primary_keys(ExtraFields.primary_id.value, YDBContextStorage._KEY_FIELD),
        )

    return await pool.retry_operation(callee)


async def _create_dict_table(pool, path, table_name):
    async def callee(session):
        await session.create_table(
            "/".join([path, table_name]),
            TableDescription()
            .with_column(Column(ExtraFields.primary_id.value, PrimitiveType.Utf8))
            .with_column(Column(ExtraFields.created_at.value, OptionalType(PrimitiveType.Timestamp)))
            .with_column(Column(ExtraFields.updated_at.value, OptionalType(PrimitiveType.Timestamp)))
            .with_column(Column(YDBContextStorage._KEY_FIELD, PrimitiveType.Utf8))
            .with_column(Column(YDBContextStorage._VALUE_FIELD, OptionalType(PrimitiveType.String)))
            .with_index(TableIndex(f"{table_name}_dictionary_index").with_index_columns(ExtraFields.primary_id.value))
            .with_primary_keys(ExtraFields.primary_id.value, YDBContextStorage._KEY_FIELD),
        )

    return await pool.retry_operation(callee)


async def _create_contexts_table(pool, path, table_name, context_schema):
    async def callee(session):
        table = (
            TableDescription()
            .with_column(Column(ExtraFields.primary_id.value, PrimitiveType.Utf8))
            .with_column(Column(ExtraFields.storage_key.value, OptionalType(PrimitiveType.Utf8)))
            .with_column(Column(ExtraFields.active_ctx.value, OptionalType(PrimitiveType.Bool)))
            .with_column(Column(ExtraFields.created_at.value, OptionalType(PrimitiveType.Timestamp)))
            .with_column(Column(ExtraFields.updated_at.value, OptionalType(PrimitiveType.Timestamp)))
            .with_index(TableIndex("general_context_key_index").with_index_columns(ExtraFields.storage_key.value))
            .with_primary_key(ExtraFields.primary_id.value)
        )

        await session.create_table("/".join([path, table_name]), table)

        for _, field_props in dict(context_schema).items():
            if isinstance(field_props, ValueSchemaField) and field_props.name not in [c.name for c in table.columns]:
                if (
                    field_props.on_read != SchemaFieldReadPolicy.IGNORE
                    or field_props.on_write != SchemaFieldWritePolicy.IGNORE
                ):
                    raise RuntimeError(
                        f"Value field `{field_props.name}` is not ignored in the scheme,"
                        "yet no columns are created for it!"
                    )

    return await pool.retry_operation(callee)
