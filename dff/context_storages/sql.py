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
from typing import Any, Callable, Collection, Dict, List, Optional, Tuple

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
from .protocol import get_protocol_install_suggestion
from .context_schema import ALL_ITEMS, ExtraFields

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
    from sqlalchemy.dialects.mysql import DATETIME, LONGBLOB
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


def _get_write_limit(dialect: str):
    if dialect == "sqlite":
        return (int(os.getenv("SQLITE_MAX_VARIABLE_NUMBER", 999)) - 10) // 4
    elif dialect == "mysql":
        return False
    elif dialect == "postgresql":
        return 32757 // 4
    else:
        return 9990 // 4


def _import_datetime_from_dialect(dialect: str) -> "DateTime":
    if dialect == "mysql":
        return DATETIME(fsp=6)
    else:
        return DateTime


def _import_pickletype_for_dialect(dialect: str) -> "PickleType":
    if dialect == "mysql":
        return PickleType(impl=LONGBLOB)
    else:
        return PickleType


def _get_current_time(dialect: str):
    if dialect == "sqlite":
        return func.strftime("%Y-%m-%d %H:%M:%f", "NOW")
    elif dialect == "mysql":
        return func.now(6)
    else:
        return func.now()

def _get_update_stmt(dialect: str, insert_stmt, columns: Collection[str], unique: Collection[str]):
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

    Context value fields are stored in table `contexts`.
    Columns of the table are: active_ctx, primary_id, storage_key, created_at and updated_at.

    Context dictionary fields are stored in tables `TABLE_NAME_PREFIX_FIELD`.
    Columns of the tables are: primary_id, key, value, created_at and updated_at,
    where key contains nested dict key and value contains nested dict value.

    Context reading is done with one query to each table.
    Context reading is done with one query to each table, but that can be optimized for PostgreSQL.

    :param path: Standard sqlalchemy URI string.
        Examples: `sqlite+aiosqlite://path_to_the_file/file_name`,
        `mysql+asyncmy://root:pass@localhost:3306/test`,
        `postgresql+asyncpg://postgres:pass@localhost:5430/test`.
    :param table_name: The name of the table to use.
    :param custom_driver: If you intend to use some other database driver instead of the recommended ones,
        set this parameter to `True` to bypass the import checks.
    """

    _CONTEXTS_TABLE = "contexts"
    _LOGS_TABLE= "logs"
    _KEY_COLUMN = "key"
    _VALUE_COLUMN = "value"
    _FIELD_COLUMN = "field"
    _PACKED_COLUMN = "data"

    _UUID_LENGTH = 64
    _FIELD_LENGTH = 256

    def __init__(self, path: str, table_name_prefix: str = "dff_table", custom_driver: bool = False):
        DBContextStorage.__init__(self, path)

        self._check_availability(custom_driver)
        self.engine = create_async_engine(self.full_path)
        self.dialect: str = self.engine.dialect.name
        self._insert_limit = _get_write_limit(self.dialect)
        self._INSERT_CALLABLE = _import_insert_for_dialect(self.dialect)

        _DATETIME_CLASS = _import_datetime_from_dialect(self.dialect)
        _PICKLETYPE_CLASS = _import_pickletype_for_dialect(self.dialect)

        self.tables_prefix = table_name_prefix
        self.context_schema.enable_async_access(self.dialect != "sqlite")

        self.tables = dict()
        current_time = _get_current_time(self.dialect)
        self.tables[self._CONTEXTS_TABLE] = Table(
            f"{table_name_prefix}_{self._CONTEXTS_TABLE}",
            MetaData(),
            Column(ExtraFields.active_ctx.value, Boolean, default=True, nullable=False),
            Column(ExtraFields.primary_id.value, String(self._UUID_LENGTH), index=True, unique=True, nullable=False),
            Column(ExtraFields.storage_key.value, String(self._UUID_LENGTH), index=True, nullable=False),
            Column(self._PACKED_COLUMN, _PICKLETYPE_CLASS, nullable=False),
            Column(ExtraFields.created_at.value, _DATETIME_CLASS, server_default=current_time, nullable=False),
            Column(
                ExtraFields.updated_at.value,
                _DATETIME_CLASS,
                server_default=current_time,
                server_onupdate=current_time,
                nullable=False,
            ),
        )
        self.tables[self._LOGS_TABLE] = Table(
            f"{table_name_prefix}_{self._LOGS_TABLE}",
            MetaData(),
            Column(ExtraFields.primary_id.value, String(self._UUID_LENGTH), index=True, nullable=False),
            Column(self._FIELD_COLUMN, String(self._FIELD_LENGTH), index=True, nullable=False),
            Column(self._KEY_COLUMN, Integer, nullable=False),
            Column(self._VALUE_COLUMN, PickleType, nullable=False),
            Column(ExtraFields.created_at.value, _DATETIME_CLASS, server_default=current_time, nullable=False),
            Column(
                ExtraFields.updated_at.value,
                _DATETIME_CLASS,
                server_default=current_time,
                server_onupdate=current_time,
                nullable=False,
            ),
            Index(f"logs_index", ExtraFields.primary_id.value, self._FIELD_COLUMN, self._KEY_COLUMN, unique=True),
        )

        asyncio.run(self._create_self_tables())

    @threadsafe_method
    @cast_key_to_string()
    async def get_item_async(self, key: str) -> Context:
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        return await self.context_schema.read_context(self._read_pac_ctx, self._read_log_ctx, key, primary_id)

    @threadsafe_method
    @cast_key_to_string()
    async def set_item_async(self, key: str, value: Context):
        primary_id = await self._get_last_ctx(key)
        await self.context_schema.write_context(value, self._write_pac_ctx, self._write_log_ctx, key, primary_id, self._insert_limit)

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: str):
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        stmt = update(self.tables[self._CONTEXTS_TABLE])
        stmt = stmt.where(self.tables[self._CONTEXTS_TABLE].c[ExtraFields.storage_key.value] == key)
        stmt = stmt.values({ExtraFields.active_ctx.value: False})
        async with self.engine.begin() as conn:
            await conn.execute(stmt)

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        return await self._get_last_ctx(key) is not None

    @threadsafe_method
    async def len_async(self) -> int:
        subq = select(self.tables[self._CONTEXTS_TABLE])
        subq = subq.where(self.tables[self._CONTEXTS_TABLE].c[ExtraFields.active_ctx.value])
        stmt = select(func.count()).select_from(subq.subquery())
        async with self.engine.begin() as conn:
            return (await conn.execute(stmt)).fetchone()[0]

    @threadsafe_method
    async def clear_async(self):
        stmt = update(self.tables[self._CONTEXTS_TABLE])
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
        ctx_table = self.tables[self._CONTEXTS_TABLE]
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

    async def _read_pac_ctx(self, _: str, primary_id: str) -> Dict:
        async with self.engine.begin() as conn:
            stmt = select(self.tables[self._CONTEXTS_TABLE].c[self._PACKED_COLUMN])
            stmt = stmt.where(self.tables[self._CONTEXTS_TABLE].c[ExtraFields.primary_id.value] == primary_id)
            result = (await conn.execute(stmt)).fetchone()
            if result is not None:
                return result[0]
            else:
                return dict()

    async def _read_log_ctx(self, keys_limit: Optional[int], keys_offset: int, field_name: str, _: str, primary_id: str) -> Dict:
        async with self.engine.begin() as conn:
            stmt = select(self.tables[self._LOGS_TABLE].c[self._KEY_COLUMN], self.tables[self._LOGS_TABLE].c[self._VALUE_COLUMN])
            stmt = stmt.where(self.tables[self._LOGS_TABLE].c[ExtraFields.primary_id.value] == primary_id)
            stmt = stmt.where(self.tables[self._LOGS_TABLE].c[self._FIELD_COLUMN] == field_name)
            stmt = stmt.order_by(self.tables[self._LOGS_TABLE].c[self._KEY_COLUMN].desc())
            if keys_limit is not None:
                stmt = stmt.limit(keys_limit)
            stmt = stmt.offset(keys_offset)
            result = (await conn.execute(stmt)).fetchall()
            if len(result) > 0:
                return {key: value for key, value in result}
            else:
                return dict()

    async def _write_pac_ctx(self, data: Dict, storage_key: str, primary_id: str):
        async with self.engine.begin() as conn:
            insert_stmt = self._INSERT_CALLABLE(self.tables[self._CONTEXTS_TABLE]).values(
                {self._PACKED_COLUMN: data, ExtraFields.storage_key.value: storage_key, ExtraFields.primary_id.value: primary_id}
            )
            update_stmt = _get_update_stmt(self.dialect, insert_stmt, [self._PACKED_COLUMN], [ExtraFields.primary_id.value])
            await conn.execute(update_stmt)

    async def _write_log_ctx(self, data: List[Tuple[str, int, Any]], _: str, primary_id: str):
        async with self.engine.begin() as conn:
            insert_stmt = self._INSERT_CALLABLE(self.tables[self._LOGS_TABLE]).values(
                [
                    {self._FIELD_COLUMN: field, self._KEY_COLUMN: key, self._VALUE_COLUMN: value, ExtraFields.primary_id.value: primary_id}
                    for field, key, value in data
                ]
            )
            update_stmt = _get_update_stmt(self.dialect, insert_stmt, [self._VALUE_COLUMN], [ExtraFields.primary_id.value, self._FIELD_COLUMN, self._KEY_COLUMN])
            await conn.execute(update_stmt)
