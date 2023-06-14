"""
SQL
---
The SQL module provides a SQL-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data from SQL databases.
It allows the DFF to easily store and retrieve context data in a format that is highly scalable
and easy to work with.

The SQL module provides the ability to choose the backend of your choice from
MySQL, PostgreSQL, or SQLite. You can choose the one that is most suitable for your use case and environment.
MySQL and PostgreSQL are widely used open-source relational databases that are known for their
reliability and scalability. SQLite is a self-contained, high-reliability, embedded, full-featured,
public-domain, SQL database engine.
"""
import asyncio
import importlib
import os
from typing import Callable, Hashable, Dict, Union, List, Iterable, Optional

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
from .protocol import get_protocol_install_suggestion
from .context_schema import (
    ALL_ITEMS,
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
    from sqlalchemy import (
        Table,
        MetaData,
        Column,
        PickleType,
        String,
        DateTime,
        Integer,
        Boolean,
        Index,
        Insert,
        inspect,
        select,
        update,
        func,
    )
    from sqlalchemy.dialects.mysql import DATETIME
    from sqlalchemy.ext.asyncio import create_async_engine

    sqlalchemy_available = True
except (ImportError, ModuleNotFoundError):
    sqlalchemy_available = False

postgres_available = sqlite_available = mysql_available = False

try:
    import asyncpg

    _ = asyncpg

    postgres_available = True
except (ImportError, ModuleNotFoundError):
    pass

try:
    import asyncmy

    _ = asyncmy

    mysql_available = True
except (ImportError, ModuleNotFoundError):
    pass

try:
    import aiosqlite

    _ = aiosqlite

    sqlite_available = True
except (ImportError, ModuleNotFoundError):
    pass

if not sqlalchemy_available:
    postgres_available = sqlite_available = mysql_available = False


def _import_insert_for_dialect(dialect: str) -> Callable[[str], "Insert"]:
    return getattr(importlib.import_module(f"sqlalchemy.dialects.{dialect}"), "insert")


def _import_datetime_from_dialect(dialect: str) -> "DateTime":
    if dialect == "mysql":
        return DATETIME(fsp=6)
    else:
        return DateTime


def _get_current_time(dialect: str):
    if dialect == "sqlite":
        return func.strftime("%Y-%m-%d %H:%M:%f", "NOW")
    elif dialect == "mysql":
        return func.now(6)
    else:
        return func.now()


def _get_write_limit(dialect: str):
    if dialect == "sqlite":
        return (os.getenv("SQLITE_MAX_VARIABLE_NUMBER", 999) - 10) // 3
    elif dialect == "mysql":
        return False
    elif dialect == "postgresql":
        return 32757 // 3
    else:
        return 9990 // 3


def _get_update_stmt(dialect: str, insert_stmt, columns: Iterable[str], unique: List[str]):
    if dialect == "postgresql" or dialect == "sqlite":
        if len(columns) > 0:
            update_stmt = insert_stmt.on_conflict_do_update(
                index_elements=unique, set_={column: insert_stmt.excluded[column] for column in columns}
            )
        else:
            update_stmt = insert_stmt.on_conflict_do_nothing()
    elif dialect == "mysql":
        if len(columns) > 0:
            update_stmt = insert_stmt.on_duplicate_key_update(
                **{column: insert_stmt.inserted[column] for column in columns}
            )
        else:
            update_stmt = insert_stmt.prefix_with("IGNORE")
    else:
        update_stmt = insert_stmt
    return update_stmt


class SQLContextStorage(DBContextStorage):
    """
    | SQL-based version of the :py:class:`.DBContextStorage`.
    | Compatible with MySQL, Postgresql, Sqlite.
    | When using Sqlite on a Windows system, keep in mind that you have to use double backslashes '\\'
    | instead of forward slashes '/' in the file path.

    :param path: Standard sqlalchemy URI string.
        Examples: `sqlite+aiosqlite://path_to_the_file/file_name`,
        `mysql+asyncmy://root:pass@localhost:3306/test`,
        `postgresql+asyncpg://postgres:pass@localhost:5430/test`.
    :param table_name: The name of the table to use.
    :param custom_driver: If you intend to use some other database driver instead of the recommended ones,
        set this parameter to `True` to bypass the import checks.
    """

    _CONTEXTS = "contexts"
    _KEY_FIELD = "key"
    _VALUE_FIELD = "value"

    _UUID_LENGTH = 36
    _KEY_LENGTH = 256

    def __init__(self, path: str, table_name_prefix: str = "dff_table", custom_driver: bool = False):
        DBContextStorage.__init__(self, path)

        self._check_availability(custom_driver)
        self.engine = create_async_engine(self.full_path)
        self.dialect: str = self.engine.dialect.name
        self._INSERT_CALLABLE = _import_insert_for_dialect(self.dialect)
        self._DATETIME_CLASS = _import_datetime_from_dialect(self.dialect)
        self._param_limit = _get_write_limit(self.dialect)

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

        self.tables_prefix = table_name_prefix

        self.tables = dict()
        current_time = _get_current_time(self.dialect)
        self.tables.update(
            {
                field: Table(
                    f"{table_name_prefix}_{field}",
                    MetaData(),
                    Column(ExtraFields.primary_id.value, String(self._UUID_LENGTH), index=True, nullable=False),
                    Column(self._KEY_FIELD, Integer, nullable=False),
                    Column(self._VALUE_FIELD, PickleType, nullable=False),
                    Index(f"{field}_list_index", ExtraFields.primary_id.value, self._KEY_FIELD, unique=True),
                )
                for field in list_fields
            }
        )
        self.tables.update(
            {
                field: Table(
                    f"{table_name_prefix}_{field}",
                    MetaData(),
                    Column(ExtraFields.primary_id.value, String(self._UUID_LENGTH), index=True, nullable=False),
                    Column(self._KEY_FIELD, String(self._KEY_LENGTH), nullable=False),
                    Column(self._VALUE_FIELD, PickleType, nullable=False),
                    Column(
                        ExtraFields.created_at.value, self._DATETIME_CLASS, server_default=current_time, nullable=False
                    ),
                    Column(
                        ExtraFields.updated_at.value,
                        self._DATETIME_CLASS,
                        server_default=current_time,
                        server_onupdate=current_time,
                        nullable=False,
                    ),
                    Index(f"{field}_dictionary_index", ExtraFields.primary_id.value, self._KEY_FIELD, unique=True),
                )
                for field in dict_fields
            }
        )
        self.tables.update(
            {
                self._CONTEXTS: Table(
                    f"{table_name_prefix}_{self._CONTEXTS}",
                    MetaData(),
                    Column(ExtraFields.active_ctx.value, Boolean(), default=True, nullable=False),
                    Column(
                        ExtraFields.primary_id.value, String(self._UUID_LENGTH), index=True, unique=True, nullable=False
                    ),
                    Column(ExtraFields.storage_key.value, String(self._UUID_LENGTH), index=True, nullable=False),
                    Column(
                        ExtraFields.created_at.value, self._DATETIME_CLASS, server_default=current_time, nullable=False
                    ),
                    Column(
                        ExtraFields.updated_at.value,
                        self._DATETIME_CLASS,
                        server_default=current_time,
                        server_onupdate=current_time,
                        nullable=False,
                    ),
                    Index("general_context_id_index", ExtraFields.primary_id.value, unique=True),
                    Index("general_context_key_index", ExtraFields.storage_key.value),
                )
            }
        )

        for _, field_props in dict(self.context_schema).items():
            if isinstance(field_props, ValueSchemaField) and field_props.name not in [
                t.name for t in self.tables[self._CONTEXTS].c
            ]:
                if (
                    field_props.on_read != SchemaFieldReadPolicy.IGNORE
                    or field_props.on_write != SchemaFieldWritePolicy.IGNORE
                ):
                    raise RuntimeError(
                        f"Value field `{field_props.name}` is not ignored in the scheme,"
                        "yet no columns are created for it!"
                    )

        asyncio.run(self._create_self_tables())

    def set_context_schema(self, scheme: ContextSchema):
        super().set_context_schema(scheme)
        params = {
            **self.context_schema.dict(),
            "active_ctx": FrozenValueSchemaField(name=ExtraFields.active_ctx, on_write=SchemaFieldWritePolicy.IGNORE),
            "created_at": ValueSchemaField(name=ExtraFields.created_at, on_write=SchemaFieldWritePolicy.IGNORE),
            "updated_at": ValueSchemaField(name=ExtraFields.updated_at, on_write=SchemaFieldWritePolicy.IGNORE),
        }
        self.context_schema = ContextSchema(**params)

    @threadsafe_method
    @cast_key_to_string()
    async def get_item_async(self, key: str) -> Context:
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.context_schema.read_context(self._read_ctx, key, primary_id)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @cast_key_to_string()
    async def set_item_async(self, key: str, value: Context):
        primary_id = await self._get_last_ctx(key)
        value_hash = self.hash_storage.get(key)
        await self.context_schema.write_context(
            value, value_hash, self._write_ctx_val, key, primary_id, self._param_limit
        )

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: str):
        self.hash_storage[key] = None
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        stmt = update(self.tables[self._CONTEXTS])
        stmt = stmt.where(self.tables[self._CONTEXTS].c[ExtraFields.storage_key.value] == key)
        stmt = stmt.values({ExtraFields.active_ctx.value: False})
        async with self.engine.begin() as conn:
            await conn.execute(stmt)

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        return await self._get_last_ctx(key) is not None

    @threadsafe_method
    async def len_async(self) -> int:
        subq = select(self.tables[self._CONTEXTS])
        subq = subq.where(self.tables[self._CONTEXTS].c[ExtraFields.active_ctx.value])
        stmt = select(func.count()).select_from(subq.subquery())
        async with self.engine.begin() as conn:
            return (await conn.execute(stmt)).fetchone()[0]

    @threadsafe_method
    async def clear_async(self):
        self.hash_storage = {key: None for key, _ in self.hash_storage.items()}
        stmt = update(self.tables[self._CONTEXTS])
        stmt = stmt.values({ExtraFields.active_ctx.value: False})
        async with self.engine.begin() as conn:
            await conn.execute(stmt)

    async def _create_self_tables(self):
        async with self.engine.begin() as conn:
            for table in self.tables.values():
                if not await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table(table.name)):
                    await conn.run_sync(table.create, self.engine)

    def _check_availability(self, custom_driver: bool):
        if not custom_driver:
            if self.full_path.startswith("postgresql") and not postgres_available:
                install_suggestion = get_protocol_install_suggestion("postgresql")
                raise ImportError("Packages `sqlalchemy` and/or `asyncpg` are missing.\n" + install_suggestion)
            elif self.full_path.startswith("mysql") and not mysql_available:
                install_suggestion = get_protocol_install_suggestion("mysql")
                raise ImportError("Packages `sqlalchemy` and/or `asyncmy` are missing.\n" + install_suggestion)
            elif self.full_path.startswith("sqlite") and not sqlite_available:
                install_suggestion = get_protocol_install_suggestion("sqlite")
                raise ImportError("Package `sqlalchemy` and/or `aiosqlite` is missing.\n" + install_suggestion)

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        ctx_table = self.tables[self._CONTEXTS]
        stmt = select(ctx_table.c[ExtraFields.primary_id.value])
        stmt = stmt.where(
            (ctx_table.c[ExtraFields.storage_key.value] == storage_key) & (ctx_table.c[ExtraFields.active_ctx.value])
        )
        stmt = stmt.limit(1)
        async with self.engine.begin() as conn:
            primary_id = (await conn.execute(stmt)).fetchone()
            if primary_id is None:
                return None
            else:
                return primary_id[0]

    # TODO: optimize for PostgreSQL: single query.
    async def _read_ctx(self, subscript: Dict[str, Union[bool, int, List[Hashable]]], primary_id: str) -> Dict:
        result_dict, values_slice = dict(), list()

        async with self.engine.begin() as conn:
            for field, value in subscript.items():
                if isinstance(value, bool) and value:
                    values_slice += [field]
                else:
                    raw_stmt = select(self.tables[field].c[self._KEY_FIELD], self.tables[field].c[self._VALUE_FIELD])
                    raw_stmt = raw_stmt.where(self.tables[field].c[ExtraFields.primary_id.value] == primary_id)

                    if isinstance(value, int):
                        if value > 0:
                            filtered_stmt = raw_stmt.order_by(self.tables[field].c[self._KEY_FIELD].asc()).limit(value)
                        else:
                            filtered_stmt = raw_stmt.order_by(self.tables[field].c[self._KEY_FIELD].desc()).limit(
                                -value
                            )
                    elif isinstance(value, list):
                        filtered_stmt = raw_stmt.where(self.tables[field].c[self._KEY_FIELD].in_(value))
                    elif value == ALL_ITEMS:
                        filtered_stmt = raw_stmt

                    for key, value in (await conn.execute(filtered_stmt)).fetchall():
                        if value is not None:
                            if field not in result_dict:
                                result_dict[field] = dict()
                            result_dict[field][key] = value

                columns = [c for c in self.tables[self._CONTEXTS].c if c.name in values_slice]
                stmt = select(*columns).where(self.tables[self._CONTEXTS].c[ExtraFields.primary_id.value] == primary_id)
                for key, value in zip([c.name for c in columns], (await conn.execute(stmt)).fetchone()):
                    if value is not None:
                        result_dict[key] = value

        return result_dict

    async def _write_ctx_val(self, field: Optional[str], payload: FieldDescriptor, nested: bool, primary_id: str):
        async with self.engine.begin() as conn:
            if nested and len(payload[0]) > 0:
                data, enforce = payload
                values = [
                    {ExtraFields.primary_id.value: primary_id, self._KEY_FIELD: key, self._VALUE_FIELD: value}
                    for key, value in data.items()
                ]
                insert_stmt = self._INSERT_CALLABLE(self.tables[field]).values(values)
                update_stmt = _get_update_stmt(
                    self.dialect,
                    insert_stmt,
                    [self._VALUE_FIELD] if enforce else [],
                    [ExtraFields.primary_id.value, self._KEY_FIELD],
                )
                await conn.execute(update_stmt)

            elif not nested and len(payload) > 0:
                values = {key: data for key, (data, _) in payload.items()}
                insert_stmt = self._INSERT_CALLABLE(self.tables[self._CONTEXTS]).values(
                    {**values, ExtraFields.primary_id.value: primary_id}
                )
                enforced_keys = set(key for key in values.keys() if payload[key][1])
                update_stmt = _get_update_stmt(self.dialect, insert_stmt, enforced_keys, [ExtraFields.primary_id.value])
                await conn.execute(update_stmt)
