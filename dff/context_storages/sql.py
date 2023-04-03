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
from typing import Hashable, Dict, Union, Any, List, Iterable
from uuid import UUID

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, auto_stringify_hashable_key
from .protocol import get_protocol_install_suggestion
from .update_scheme import UpdateScheme, FieldType, ExtraFields, FieldRule, UpdateSchemeBuilder

try:
    from sqlalchemy import Table, MetaData, Column, PickleType, String, DateTime, TIMESTAMP, Integer, UniqueConstraint, Index, inspect, select, delete, func
    from sqlalchemy.dialects import mysql
    from sqlalchemy.dialects.sqlite import DATETIME
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


def _import_insert_for_dialect(dialect: str):
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
        _import_insert_for_dialect(self.dialect)

        self.list_fields = [field for field in UpdateScheme.ALL_FIELDS if self.update_scheme.fields[field]["type"] == FieldType.LIST]
        self.dict_fields = [field for field in UpdateScheme.ALL_FIELDS if self.update_scheme.fields[field]["type"] == FieldType.DICT]
        self.value_fields = list(UpdateScheme.EXTRA_FIELDS)
        self.all_fields = self.list_fields + self.dict_fields + self.value_fields

        self.tables_prefix = table_name_prefix

        self.tables = dict()
        current_time = func.STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')
        self.tables.update({field: Table(
            f"{table_name_prefix}_{field}",
            MetaData(),
            Column(ExtraFields.IDENTITY_FIELD, String(self._UUID_LENGTH), nullable=False),
            Column(self._KEY_FIELD, Integer, nullable=False),
            Column(self._VALUE_FIELD, PickleType, nullable=False),
            Index(f"{field}_list_index", ExtraFields.IDENTITY_FIELD, self._KEY_FIELD, unique=True)
        ) for field in self.list_fields})
        self.tables.update({field: Table(
            f"{table_name_prefix}_{field}",
            MetaData(),
            Column(ExtraFields.IDENTITY_FIELD, String(self._UUID_LENGTH), nullable=False),
            Column(self._KEY_FIELD, String(self._KEY_LENGTH), nullable=False),
            Column(self._VALUE_FIELD, PickleType, nullable=False),
            Index(f"{field}_dictionary_index", ExtraFields.IDENTITY_FIELD, self._KEY_FIELD, unique=True)
        ) for field in self.dict_fields})
        self.tables.update({self._CONTEXTS: Table(
            f"{table_name_prefix}_{self._CONTEXTS}",
            MetaData(),
            Column(ExtraFields.IDENTITY_FIELD, String(self._UUID_LENGTH), primary_key=True, unique=True, nullable=True),
            Column(ExtraFields.EXTERNAL_FIELD, String(self._UUID_LENGTH), index=True, nullable=False),
            Column(ExtraFields.CREATED_AT_FIELD, DateTime, server_default=current_time, nullable=False),
            Column(ExtraFields.UPDATED_AT_FIELD, DateTime, server_default=current_time, server_onupdate=current_time, nullable=False),
        )})  # We DO assume this mapping of fields to be excessive (self.value_fields).

        for field in UpdateScheme.ALL_FIELDS:
            if self.update_scheme.fields[field]["type"] == FieldType.VALUE and field not in self.value_fields:
                if self.update_scheme.fields[field]["read"] != FieldRule.IGNORE or self.update_scheme.fields[field]["write"] != FieldRule.IGNORE:
                    raise RuntimeError(f"Value field `{field}` is not ignored in the scheme, yet no columns are created for it!")

        asyncio.run(self._create_self_tables())

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
        async with self.engine.begin() as conn:
            await conn.execute(self.tables[self._CONTEXTS].insert().values({ExtraFields.IDENTITY_FIELD: None, ExtraFields.EXTERNAL_FIELD: key}))

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        stmt = select(self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD]).where(self.tables[self._CONTEXTS].c[ExtraFields.EXTERNAL_FIELD] == key).order_by(self.tables[self._CONTEXTS].c[ExtraFields.CREATED_AT_FIELD].desc())
        async with self.engine.begin() as conn:
            result = (await conn.execute(stmt)).fetchone()
            return result[0] is not None

    @threadsafe_method
    async def len_async(self) -> int:
        stmt = select(self.tables[self._CONTEXTS]).where(self.tables[self._CONTEXTS].c[ExtraFields.EXTERNAL_FIELD] != None).group_by(self.tables[self._CONTEXTS].c[ExtraFields.EXTERNAL_FIELD])
        stmt = select(func.count()).select_from(stmt.subquery())
        async with self.engine.begin() as conn:
            return (await conn.execute(stmt)).fetchone()[0]

    @threadsafe_method
    async def clear_async(self):
        for table in self.tables.values():
            async with self.engine.begin() as conn:
                await conn.execute(delete(table))

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

    async def _get_update_stmt(self, insert_stmt, columns: Iterable[str], unique: List[str]):
        if self.dialect == "postgresql" or self.dialect == "sqlite":
            update_stmt = insert_stmt.on_conflict_do_update(index_elements=unique, set_={column: insert_stmt.excluded[column] for column in columns})
        elif self.dialect == "mysql":
            update_stmt = insert_stmt.on_duplicate_key_update(**{column: insert_stmt.inserted[column] for column in columns})
        else:
            update_stmt = insert_stmt
        return update_stmt

    async def _read_keys(self, ext_id: Union[UUID, int, str]) -> Dict[str, List[str]]:
        key_columns = list()
        joined_table = self.tables[self._CONTEXTS]
        for field in self.list_fields + self.dict_fields:
            condition = self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD] == self.tables[field].c[ExtraFields.IDENTITY_FIELD]
            joined_table = joined_table.join(self.tables[field], condition, isouter=True)
            key_columns += [self.tables[field].c[self._KEY_FIELD]]

        request = select(self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD]).where(self.tables[self._CONTEXTS].c[ExtraFields.EXTERNAL_FIELD] == ext_id).order_by(self.tables[self._CONTEXTS].c[ExtraFields.CREATED_AT_FIELD].desc()).limit(1)
        stmt = select(*key_columns).select_from(joined_table)
        stmt = stmt.where(self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD] == request.subquery().c[ExtraFields.IDENTITY_FIELD])

        key_dict = dict()
        async with self.engine.connect() as conn:
            for result in (await conn.execute(stmt)).fetchall():
                logger.warning(f"FIELD: {result}")
                for key, value in zip(key_columns, result):
                    field_name = str(key).removeprefix(f"{self.tables_prefix}_").split(".")[0]
                    if value is not None and field_name not in key_dict:
                        if field_name not in key_dict:
                            key_dict[field_name] = list()
                        key_dict[field_name] += [value]
        logger.warning(f"FIELDS '{ext_id}': {key_dict}")
        return key_dict

    async def _read_ctx(self, outlook: Dict[str, Union[bool, Dict[Hashable, bool]]], _: str, ext_id: Union[UUID, int, str]) -> Dict:
        key_columns = list()
        value_columns = list()
        joined_table = self.tables[self._CONTEXTS]
        for field in self.list_fields + self.dict_fields:
            condition = self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD] == self.tables[field].c[ExtraFields.IDENTITY_FIELD]
            joined_table = joined_table.join(self.tables[field], condition, isouter=True)
            key_columns += [self.tables[field].c[self._KEY_FIELD]]
            value_columns += [self.tables[field].c[self._VALUE_FIELD]]

        request = select(self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD]).where(self.tables[self._CONTEXTS].c[ExtraFields.EXTERNAL_FIELD] == ext_id).order_by(self.tables[self._CONTEXTS].c[ExtraFields.CREATED_AT_FIELD].desc()).limit(1)
        stmt = select(*self.tables[self._CONTEXTS].c, *key_columns, *value_columns).select_from(joined_table)
        stmt = stmt.where(self.tables[self._CONTEXTS].c[ExtraFields.IDENTITY_FIELD] == request.subquery().c[ExtraFields.IDENTITY_FIELD])

        key_dict = dict()
        async with self.engine.connect() as conn:
            values_len = len(self.tables[self._CONTEXTS].c)
            columns = list(self.tables[self._CONTEXTS].c) + key_columns + value_columns
            for result in (await conn.execute(stmt)).fetchall():
                sequence_result = zip(result[values_len:values_len + len(key_columns)], result[values_len + len(key_columns): values_len + len(key_columns) + len(value_columns)])
                for key, value in zip(columns[:values_len], result[:values_len]):
                    field_name = str(key).removeprefix(f"{self.tables_prefix}_").split(".")[-1]
                    if value is not None and field_name not in key_dict:
                        key_dict[field_name] = value
                for key, (outer_value, inner_value) in zip(columns[values_len:values_len + len(key_columns)], sequence_result):
                    field_name = str(key).removeprefix(f"{self.tables_prefix}_").split(".")[0]
                    if outer_value is not None and inner_value is not None:
                        if field_name not in key_dict:
                            key_dict[field_name] = dict()
                        key_dict[field_name].update({outer_value: inner_value})
            logger.warning(f"READ '{ext_id}': {key_dict}")
        return key_dict

    async def _write_ctx(self, data: Dict[str, Any], int_id: str, __: Union[UUID, int, str]):
        logger.warning(f"WRITE '{__}': {data}")
        async with self.engine.begin() as conn:
            for field, storage in {k: v for k, v in data.items() if isinstance(v, dict)}.items():
                if len(storage.items()) > 0:
                    values = [{ExtraFields.IDENTITY_FIELD: int_id, self._KEY_FIELD: key, self._VALUE_FIELD: value} for key, value in storage.items()]
                    insert_stmt = insert(self.tables[field]).values(values)
                    update_stmt = await self._get_update_stmt(insert_stmt, [column.name for column in self.tables[field].c], [ExtraFields.IDENTITY_FIELD, self._KEY_FIELD])
                    await conn.execute(update_stmt)
            values = {k: v for k, v in data.items() if not isinstance(v, dict)}
            if len(values.items()) > 0:
                insert_stmt = insert(self.tables[self._CONTEXTS]).values({**values, ExtraFields.IDENTITY_FIELD: int_id})
                update_stmt = await self._get_update_stmt(insert_stmt, values.keys(), [ExtraFields.IDENTITY_FIELD])
                await conn.execute(update_stmt)
