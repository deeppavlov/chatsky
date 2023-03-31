"""
SQL
---
The SQL module provides a SQL-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data from SQL databases.
It allows the `DFF` to easily store and retrieve context data in a format that is highly scalable
and easy to work with.

The SQL module provides the ability to choose the backend of your choice from
MySQL, PostgreSQL, or SQLite. You can choose the one that is most suitable for your use case and environment.
MySQL and PostgreSQL are widely used open-source relational databases that are known for their
reliability and scalability. SQLite is a self-contained, high-reliability, embedded, full-featured,
public-domain, SQL database engine.
"""
import asyncio
import importlib
import logging
from typing import Hashable, Dict, Union, Any
from uuid import UUID

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, auto_stringify_hashable_key
from .protocol import get_protocol_install_suggestion
from .update_scheme import UpdateScheme, FieldType, ExtraFields, FieldRule, UpdateSchemeBuilder

try:
    from sqlalchemy import Table, MetaData, Column, JSON, String, DateTime, Integer, UniqueConstraint, Index, inspect, select, delete, func
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

    :param dialect: Chosen sqlalchemy dialect.
    """
    global insert
    insert = getattr(
        importlib.import_module(f"sqlalchemy.dialects.{dialect}"),
        "insert",
    )


logger = logging.getLogger(__name__)


class SQLContextStorage(DBContextStorage):
    """
    | SQL-based version of the :py:class:`.DBContextStorage`.
    | Compatible with MySQL, Postgresql, Sqlite.

    :param path: Standard sqlalchemy URI string.
        When using sqlite backend in Windows, keep in mind that you have to use double backslashes '\\'
        instead of forward slashes '/' in the file path.
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

        self.list_fields = [field for field in UpdateScheme.ALL_FIELDS if self.update_scheme.fields[field]["type"] == FieldType.LIST]
        self.dict_fields = [field for field in UpdateScheme.ALL_FIELDS if self.update_scheme.fields[field]["type"] == FieldType.DICT]
        self.value_fields = list(UpdateScheme.EXTRA_FIELDS)
        self.all_fields = self.list_fields + self.dict_fields + self.value_fields

        self.tables = dict()
        self.tables.update({field: Table(
            f"{table_name_prefix}_{field}",
            MetaData(),
            Column(ExtraFields.IDENTITY_FIELD, String(self._UUID_LENGTH)),
            Column(self._KEY_FIELD, Integer()),
            Column(self._VALUE_FIELD, JSON),
            Index(f"{field}_list_index", ExtraFields.IDENTITY_FIELD, self._KEY_FIELD, unique=True)
        ) for field in self.list_fields})
        self.tables.update({field: Table(
            f"{table_name_prefix}_{field}",
            MetaData(),
            Column(ExtraFields.IDENTITY_FIELD, String(self._UUID_LENGTH)),
            Column(self._KEY_FIELD, String(self._KEY_LENGTH)),
            Column(self._VALUE_FIELD, JSON),
            Index(f"{field}_dictionary_index", ExtraFields.IDENTITY_FIELD, self._KEY_FIELD, unique=True)
        ) for field in self.dict_fields})
        self.tables.update({self._CONTEXTS: Table(
            f"{table_name_prefix}_{self._CONTEXTS}",
            MetaData(),
            Column(ExtraFields.IDENTITY_FIELD, String(self._UUID_LENGTH), primary_key=True, unique=True),
            Column(ExtraFields.EXTERNAL_FIELD, String(self._UUID_LENGTH), index=True),
            Column(ExtraFields.CREATED_AT_FIELD, DateTime(), server_default=func.now()),
            Column(ExtraFields.UPDATED_AT_FIELD, DateTime(), onupdate=func.now()),
        )})  # We DO assume this mapping of fields to be excessive (self.value_fields).

        for field in UpdateScheme.ALL_FIELDS:
            if self.update_scheme.fields[field]["type"] == FieldType.VALUE and field not in self.value_fields:
                if self.update_scheme.fields[field]["read"] != FieldRule.IGNORE or self.update_scheme.fields[field]["write"] != FieldRule.IGNORE:
                    raise RuntimeError(f"Value field `{field}` is not ignored in the scheme, yet no columns are created for it!")

        asyncio.run(self._create_self_tables())
        import_insert_for_dialect(self.dialect)

    def set_update_scheme(self, scheme: Union[UpdateScheme, UpdateSchemeBuilder]):
        super().set_update_scheme(scheme)
        self.update_scheme.fields[ExtraFields.IDENTITY_FIELD].update(write=FieldRule.UPDATE_ONCE)
        self.update_scheme.fields[ExtraFields.EXTERNAL_FIELD].update(write=FieldRule.UPDATE_ONCE)

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        fields = await self._read_keys(key)
        if len(fields) == 0:
            raise KeyError(f"No entry for key {key} {fields}.")
        context, hashes = await self.update_scheme.read_context(fields, self._read_ctx, key, None)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        fields = await self._read_keys(key)
        value_hash = self.hash_storage.get(key, None)
        await self.update_scheme.write_context(value, value_hash, fields, self._write_ctx, key)

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def del_item_async(self, key: Union[Hashable, str]):
        stmt = insert(self.tables[self._CONTEXTS]).values(**{ExtraFields.IDENTITY_FIELD: None, ExtraFields.EXTERNAL_FIELD: key})
        async with self.engine.connect() as conn:
            await conn.execute(stmt)
            await conn.commit()

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        stmt = select(self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD]).where(self.tables[self._CONTEXTS].c[ExtraFields.EXTERNAL_FIELD] == key).order_by(self.tables[self._CONTEXTS].c[ExtraFields.CREATED_AT_FIELD].desc())
        async with self.engine.connect() as conn:
            result = (await conn.execute(stmt)).fetchone()
            logger.warning(f"Fetchone: {result}")
            return result[0] is not None

    @threadsafe_method
    async def len_async(self) -> int:
        stmt = select(self.tables[self._CONTEXTS]).where(self.tables[self._CONTEXTS].c[ExtraFields.EXTERNAL_FIELD] != None).group_by(self.tables[self._CONTEXTS].c[ExtraFields.EXTERNAL_FIELD])
        stmt = select(func.count()).select_from(stmt)
        async with self.engine.connect() as conn:
            return (await conn.execute(stmt)).fetchone()[0]

    @threadsafe_method
    async def clear_async(self):
        for table in self.tables.values():
            async with self.engine.connect() as conn:
                await conn.execute(delete(table))
                await conn.commit()

    async def _create_self_tables(self):
        async with self.engine.begin() as conn:
            for table in self.tables.values():
                if not await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table(table.name)):
                    await conn.run_sync(table.create, self.engine)

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

    async def _read_keys(self, ext_id: Union[UUID, int, str]) -> Dict[str, Union[bool, Dict[str, bool]]]:
        key_columns = list()
        joined_table = self.tables[self._CONTEXTS]
        for field in self.list_fields + self.dict_fields:
            condition = self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD] == self.tables[field].c[ExtraFields.IDENTITY_FIELD]
            joined_table = joined_table.join(self.tables[field], condition)
            key_columns += [self.tables[field].c[self._KEY_FIELD]]

        stmt = select(*key_columns, self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD]).select_from(joined_table)
        stmt = stmt.where(self.tables[self._CONTEXTS].c[ExtraFields.EXTERNAL_FIELD] == ext_id)
        stmt = stmt.order_by(self.tables[self._CONTEXTS].c[ExtraFields.CREATED_AT_FIELD].desc()).limit(1)

        key_dict = dict()
        async with self.engine.connect() as conn:
            for key in (await conn.execute(stmt)).fetchall():
                key_dict[key] = True
        return key_dict

    async def _read_ctx(self, outlook: Dict[Hashable, Any], _: str, ext_id: Union[UUID, int, str]) -> Dict:
        joined_table = self.tables[self._CONTEXTS]
        for field in self.list_fields + self.dict_fields:
            condition = self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD] == self.tables[field].c[ExtraFields.IDENTITY_FIELD]
            joined_table = joined_table.join(self.tables[field], condition)

        stmt = select(*[column for table in self.tables.values() for column in table.columns]).select_from(joined_table)
        stmt = stmt.where(self.tables[self._CONTEXTS].c[ExtraFields.EXTERNAL_FIELD] == ext_id)
        stmt = stmt.order_by(self.tables[self._CONTEXTS].c[ExtraFields.CREATED_AT_FIELD].desc()).limit(1)

        key_dict = dict()
        async with self.engine.connect() as conn:
            for key in (await conn.execute(stmt)).fetchall():
                key_dict[key] = True
        return key_dict

    async def _write_ctx(self, data: Dict[str, Any], _: str, __: Union[UUID, int, str]):
        async with self.engine.begin() as conn:
            for key, value in {k: v for k, v in data.items() if isinstance(v, dict)}.items():
                await conn.execute(insert(self.tables[key]).values(value))
            values = {k: v for k, v in data.items() if not isinstance(v, dict)}
            await conn.execute(insert(self.tables[self._CONTEXTS]).values(**values))
            await conn.commit()
