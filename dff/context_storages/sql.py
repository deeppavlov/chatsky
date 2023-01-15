"""
SQL
---
Provides the SQL-based version of the :py:class:`.DBContextStorage`.
You can choose the backend option of your liking from MySQL, PostgreSQL, or SQLite.
"""
import asyncio
import importlib
import json
from typing import Any

from dff.script import Context

from .database import DBContextStorage, threadsafe_method
from .protocol import get_protocol_install_suggestion

try:
    from sqlalchemy import Table, MetaData, Column, JSON, String, inspect, select, delete, func
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


def import_insert_for_dialect(dialect: str):
    """
    Imports the insert function into global scope depending on the chosen sqlalchemy dialect.
    """
    global insert
    insert = getattr(
        importlib.import_module(f"sqlalchemy.dialects.{dialect}"),
        "insert",
    )


class SQLContextStorage(DBContextStorage):
    """
    | SQL-based version of the :py:class:`.DBContextStorage`.
    | Compatible with MySQL, Postgresql, Sqlite.

    :param path: Standard sqlalchemy URI string.
        When using sqlite backend in Windows, keep in mind that you have to use double backslashes '\\'
        instead of forward slashes '/' in the file path.
    :type path: str
    :param table_name: The name of the table to use.
    :type table_name: str
    :param custom_driver: If you intend to use some other database driver instead of the recommended ones,
        set this parameter to `True` to bypass the import checks.
    :type custom_driver: bool
    """

    def __init__(self, path: str, table_name: str = "contexts", custom_driver: bool = False):
        super(SQLContextStorage, self).__init__(path)

        self._check_availability(custom_driver)
        self.engine = create_async_engine(self.full_path)
        self.dialect: str = self.engine.dialect.name

        id_column_args = {"primary_key": True}
        if self.dialect == "sqlite":
            id_column_args["sqlite_on_conflict_primary_key"] = "REPLACE"

        self.metadata = MetaData()
        self.table = Table(
            table_name,
            self.metadata,
            Column("id", String(36), **id_column_args),
            Column("context", JSON),  # column for storing serialized contexts
        )

        asyncio.run(self._create_self_table())

        import_insert_for_dialect(self.dialect)

    @threadsafe_method
    async def setitem(self, key: Any, value: Context):
        key = str(key)
        value = value if isinstance(value, Context) else Context.cast(value)
        value = json.loads(value.json())

        insert_stmt = insert(self.table).values(id=key, context=value)
        update_stmt = await self._get_update_stmt(insert_stmt)

        async with self.engine.connect() as conn:
            await conn.execute(update_stmt)
            await conn.commit()

    @threadsafe_method
    async def getitem(self, key: Any) -> Context:
        key = str(key)
        stmt = select(self.table.c.context).where(self.table.c.id == key)
        async with self.engine.connect() as conn:
            result = await conn.execute(stmt)
            row = result.fetchone()
            if row:
                return Context.cast(row[0])
        raise KeyError

    @threadsafe_method
    async def delitem(self, key: str) -> None:
        key = str(key)
        stmt = delete(self.table).where(self.table.c.id == key)
        async with self.engine.connect() as conn:
            await conn.execute(stmt)
            await conn.commit()

    @threadsafe_method
    async def contains(self, key: str) -> bool:
        key = str(key)
        stmt = select(self.table.c.context).where(self.table.c.id == key)
        async with self.engine.connect() as conn:
            result = await conn.execute(stmt)
            return bool(result.fetchone())

    @threadsafe_method
    async def len(self) -> int:
        stmt = select([func.count()]).select_from(self.table)
        async with self.engine.connect() as conn:
            result = await conn.execute(stmt)
            return result.fetchone()[0]

    @threadsafe_method
    async def clear_async(self) -> None:
        stmt = delete(self.table)
        async with self.engine.connect() as conn:
            await conn.execute(stmt)
            await conn.commit()

    async def _create_self_table(self):
        async with self.engine.begin() as conn:
            if not await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table(self.table.name)):
                await conn.run_sync(self.table.create, self.engine)

    async def _get_update_stmt(self, insert_stmt):
        if self.dialect == "sqlite":
            return insert_stmt
        elif self.dialect == "mysql":
            update_stmt = insert_stmt.on_duplicate_key_update(context=insert_stmt.inserted.context)
        else:
            update_stmt = insert_stmt.on_conflict_do_update(
                index_elements=["id"], set_=dict(context=insert_stmt.excluded.context)
            )
        return update_stmt

    def _check_availability(self, custom_driver: bool) -> None:
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
