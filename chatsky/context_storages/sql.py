"""
SQL
---
The SQL module provides a SQL-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data from SQL databases.
It allows Chatsky to easily store and retrieve context data in a format that is highly scalable
and easy to work with.

The SQL module provides the ability to choose the backend of your choice from
MySQL, PostgreSQL, or SQLite. You can choose the one that is most suitable for your use case and environment.
MySQL and PostgreSQL are widely used open-source relational databases that are known for their
reliability and scalability. SQLite is a self-contained, high-reliability, embedded, full-featured,
public-domain, SQL database engine.
"""

from __future__ import annotations
import asyncio
from importlib import import_module
from os import getenv
from typing import Callable, Collection, List, Optional, Set, Tuple
import logging

from chatsky.utils.logging import collapse_num_list
from .database import DBContextStorage, _SUBSCRIPT_DICT
from .protocol import get_protocol_install_suggestion

try:
    from sqlalchemy import (
        Table,
        MetaData,
        Column,
        LargeBinary,
        String,
        BigInteger,
        ForeignKey,
        Integer,
        Index,
        Insert,
        inspect,
        select,
        delete,
        event,
    )
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


logger = logging.getLogger(__name__)


def _sqlite_enable_foreign_key(dbapi_con, con_record):
    dbapi_con.execute("pragma foreign_keys=ON")


def _import_insert_for_dialect(dialect: str) -> Callable[[str], "Insert"]:
    return getattr(import_module(f"sqlalchemy.dialects.{dialect}"), "insert")


def _get_write_limit(dialect: str):
    if dialect == "sqlite":
        return (int(getenv("SQLITE_MAX_VARIABLE_NUMBER", 999)) - 10) // 4
    elif dialect == "mysql":
        return False
    elif dialect == "postgresql":
        return 32757 // 4
    else:
        return 9990 // 4


def _get_upsert_stmt(dialect: str, insert_stmt, columns: Collection[str], unique: Collection[str]):
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

    CONTEXT table is represented by `contexts` table.
    Columns of the table are: active_ctx, id, storage_key, data, created_at and updated_at.

    LOGS table is represented by `logs` table.
    Columns of the table are: id, field, key, value and updated_at.

    :param path: Standard sqlalchemy URI string.
        Examples: `sqlite+aiosqlite://path_to_the_file/file_name`,
        `mysql+asyncmy://root:pass@localhost:3306/test`,
        `postgresql+asyncpg://postgres:pass@localhost:5430/test`.
    :param context_schema: Context schema for this storage.
    :param serializer: Serializer that will be used for serializing contexts.
    :param table_name_prefix: "namespace" prefix for the two tables created for context storing.
    :param custom_driver: If you intend to use some other database driver instead of the recommended ones,
        set this parameter to `True` to bypass the import checks.
    """

    _UUID_LENGTH = 64

    def __init__(
        self,
        path: str,
        rewrite_existing: bool = False,
        configuration: Optional[_SUBSCRIPT_DICT] = None,
        table_name_prefix: str = "chatsky_table",
    ):
        DBContextStorage.__init__(self, path, rewrite_existing, configuration)

        self._check_availability()
        self.engine = create_async_engine(self.full_path, pool_pre_ping=True)
        self.dialect: str = self.engine.dialect.name
        self._insert_limit = _get_write_limit(self.dialect)
        self._INSERT_CALLABLE = _import_insert_for_dialect(self.dialect)

        if self.dialect == "sqlite":
            event.listen(self.engine.sync_engine, "connect", _sqlite_enable_foreign_key)

        metadata = MetaData()
        self.main_table = Table(
            f"{table_name_prefix}_{self._main_table_name}",
            metadata,
            Column(self._id_column_name, String(self._UUID_LENGTH), index=True, unique=True, nullable=False),
            Column(self._current_turn_id_column_name, BigInteger(), nullable=False),
            Column(self._created_at_column_name, BigInteger(), nullable=False),
            Column(self._updated_at_column_name, BigInteger(), nullable=False),
            Column(self._misc_column_name, LargeBinary(), nullable=False),
            Column(self._framework_data_column_name, LargeBinary(), nullable=False),
        )
        self.turns_table = Table(
            f"{table_name_prefix}_{self._turns_table_name}",
            metadata,
            Column(
                self._id_column_name,
                String(self._UUID_LENGTH),
                ForeignKey(self.main_table.name, self._id_column_name),
                nullable=False,
            ),
            Column(self._key_column_name, Integer(), nullable=False),
            Column(self._labels_field_name, LargeBinary(), nullable=True),
            Column(self._requests_field_name, LargeBinary(), nullable=True),
            Column(self._responses_field_name, LargeBinary(), nullable=True),
            Index(f"{self._turns_table_name}_index", self._id_column_name, self._key_column_name, unique=True),
        )

        asyncio.run(self._create_self_tables())

    @property
    def is_concurrent(self) -> bool:
        return self.dialect != "sqlite"

    async def _create_self_tables(self):
        """
        Create tables required for context storing, if they do not exist yet.
        """
        async with self.engine.begin() as conn:
            for table in [self.main_table, self.turns_table]:
                if not await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table(table.name)):
                    logger.debug(f"SQL table created: {table.name}")
                    await conn.run_sync(table.create, self.engine)
                else:
                    logger.debug(f"SQL table already exists: {table.name}")

    def _check_availability(self):
        """
        Chech availability of the specified backend, raise error if not available.

        :param custom_driver: custom driver is requested - no checks will be performed.
        """
        if self.full_path.startswith("postgresql") and not postgres_available:
            install_suggestion = get_protocol_install_suggestion("postgresql")
            raise ImportError("Packages `sqlalchemy` and/or `asyncpg` are missing.\n" + install_suggestion)
        elif self.full_path.startswith("mysql") and not mysql_available:
            install_suggestion = get_protocol_install_suggestion("mysql")
            raise ImportError("Packages `sqlalchemy` and/or `asyncmy` are missing.\n" + install_suggestion)
        elif self.full_path.startswith("sqlite") and not sqlite_available:
            install_suggestion = get_protocol_install_suggestion("sqlite")
            raise ImportError("Package `sqlalchemy` and/or `aiosqlite` is missing.\n" + install_suggestion)

    @DBContextStorage._lock
    async def _load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes, bytes]]:
        stmt = select(self.main_table).where(self.main_table.c[self._id_column_name] == ctx_id)
        async with self.engine.begin() as conn:
            result = (await conn.execute(stmt)).fetchone()
            return None if result is None else result[1:]

    @DBContextStorage._lock
    async def _update_main_info(
        self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, misc: bytes, fw_data: bytes
    ) -> None:
        insert_stmt = self._INSERT_CALLABLE(self.main_table).values(
            {
                self._id_column_name: ctx_id,
                self._current_turn_id_column_name: turn_id,
                self._created_at_column_name: crt_at,
                self._updated_at_column_name: upd_at,
                self._misc_column_name: misc,
                self._framework_data_column_name: fw_data,
            }
        )
        update_stmt = _get_upsert_stmt(
            self.dialect,
            insert_stmt,
            [
                self._updated_at_column_name,
                self._current_turn_id_column_name,
                self._misc_column_name,
                self._framework_data_column_name,
            ],
            [self._id_column_name],
        )
        async with self.engine.begin() as conn:
            await conn.execute(update_stmt)

    # TODO: use foreign keys instead maybe?
    @DBContextStorage._lock
    async def _delete_context(self, ctx_id: str) -> None:
        async with self.engine.begin() as conn:
            await asyncio.gather(
                conn.execute(delete(self.main_table).where(self.main_table.c[self._id_column_name] == ctx_id)),
                conn.execute(delete(self.turns_table).where(self.turns_table.c[self._id_column_name] == ctx_id)),
            )

    @DBContextStorage._lock
    async def _load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[int, bytes]]:
        logger.debug(f"Loading latest items for {ctx_id}, {field_name}...")
        stmt = select(self.turns_table.c[self._key_column_name], self.turns_table.c[field_name])
        stmt = stmt.where(self.turns_table.c[self._id_column_name] == ctx_id)
        stmt = stmt.where(self.turns_table.c[field_name] != None)
        stmt = stmt.order_by(self.turns_table.c[self._key_column_name].desc())
        if isinstance(self._subscripts[field_name], int):
            stmt = stmt.limit(self._subscripts[field_name])
        elif isinstance(self._subscripts[field_name], Set):
            stmt = stmt.where(self.turns_table.c[self._key_column_name].in_(self._subscripts[field_name]))
        async with self.engine.begin() as conn:
            return list((await conn.execute(stmt)).fetchall())

    @DBContextStorage._lock
    async def _load_field_keys(self, ctx_id: str, field_name: str) -> List[int]:
        logger.debug(f"Loading field keys for {ctx_id}, {field_name}...")
        stmt = select(self.turns_table.c[self._key_column_name])
        stmt = stmt.where(self.turns_table.c[self._id_column_name] == ctx_id)
        stmt = stmt.where(self.turns_table.c[field_name] != None)
        async with self.engine.begin() as conn:
            return [k[0] for k in (await conn.execute(stmt)).fetchall()]

    @DBContextStorage._lock
    async def _load_field_items(self, ctx_id: str, field_name: str, keys: List[int]) -> List[Tuple[int, bytes]]:
        logger.debug(f"Loading field items for {ctx_id}, {field_name} ({collapse_num_list(keys)})...")
        stmt = select(self.turns_table.c[self._key_column_name], self.turns_table.c[field_name])
        stmt = stmt.where(self.turns_table.c[self._id_column_name] == ctx_id)
        stmt = stmt.where(self.turns_table.c[self._key_column_name].in_(tuple(keys)))
        stmt = stmt.where(self.turns_table.c[field_name] != None)
        async with self.engine.begin() as conn:
            return list((await conn.execute(stmt)).fetchall())

    @DBContextStorage._lock
    async def _update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[int, Optional[bytes]]]) -> None:
        insert_stmt = self._INSERT_CALLABLE(self.turns_table).values(
            [
                {
                    self._id_column_name: ctx_id,
                    self._key_column_name: k,
                    field_name: v,
                }
                for k, v in items
            ]
        )
        update_stmt = _get_upsert_stmt(
            self.dialect,
            insert_stmt,
            [field_name],
            [self._id_column_name, self._key_column_name],
        )
        async with self.engine.begin() as conn:
            await conn.execute(update_stmt)

    @DBContextStorage._lock
    async def _clear_all(self) -> None:
        async with self.engine.begin() as conn:
            await asyncio.gather(conn.execute(delete(self.main_table)), conn.execute(delete(self.turns_table)))
