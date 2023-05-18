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
from typing import Hashable, Dict, Union, Any, List, Iterable, Tuple, Optional

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
from .protocol import get_protocol_install_suggestion
from .context_schema import (
    ContextSchema,
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
        Index,
        inspect,
        select,
        func,
        insert,
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


def _import_insert_for_dialect(dialect: str):
    """
    Imports the insert function into global scope depending on the chosen sqlalchemy dialect.
    :param dialect: Chosen sqlalchemy dialect.
    """
    global insert
    insert = getattr(importlib.import_module(f"sqlalchemy.dialects.{dialect}"), "insert")


def _import_datetime_from_dialect(dialect: str):
    global DateTime
    if dialect == "mysql":
        DateTime = DATETIME(fsp=6)


def _get_current_time(dialect: str):
    if dialect == "sqlite":
        return func.strftime("%Y-%m-%d %H:%M:%f", "NOW")
    elif dialect == "mysql":
        return func.now(6)
    else:
        return func.now()


def _get_update_stmt(dialect: str, insert_stmt, columns: Iterable[str], unique: List[str]):
    if dialect == "postgresql" or dialect == "sqlite":
        update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=unique, set_={column: insert_stmt.excluded[column] for column in columns}
        )
    elif dialect == "mysql":
        update_stmt = insert_stmt.on_duplicate_key_update(
            **{column: insert_stmt.inserted[column] for column in columns}
        )
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
        _import_insert_for_dialect(self.dialect)
        _import_datetime_from_dialect(self.dialect)

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
                    Column(self.context_schema.id.name, String(self._UUID_LENGTH), nullable=False),
                    Column(self._KEY_FIELD, Integer, nullable=False),
                    Column(self._VALUE_FIELD, PickleType, nullable=False),
                    Index(f"{field}_list_index", self.context_schema.id.name, self._KEY_FIELD, unique=True),
                )
                for field in list_fields
            }
        )
        self.tables.update(
            {
                field: Table(
                    f"{table_name_prefix}_{field}",
                    MetaData(),
                    Column(self.context_schema.id.name, String(self._UUID_LENGTH), nullable=False),
                    Column(self._KEY_FIELD, String(self._KEY_LENGTH), nullable=False),
                    Column(self._VALUE_FIELD, PickleType, nullable=False),
                    Index(f"{field}_dictionary_index", self.context_schema.id.name, self._KEY_FIELD, unique=True),
                )
                for field in dict_fields
            }
        )
        self.tables.update(
            {
                self._CONTEXTS: Table(
                    f"{table_name_prefix}_{self._CONTEXTS}",
                    MetaData(),
                    Column(
                        self.context_schema.id.name, String(self._UUID_LENGTH), index=True, unique=True, nullable=True
                    ),
                    Column(self.context_schema.ext_id.name, String(self._UUID_LENGTH), index=True, nullable=False),
                    Column(self.context_schema.created_at.name, DateTime, server_default=current_time, nullable=False),
                    Column(
                        self.context_schema.updated_at.name,
                        DateTime,
                        server_default=current_time,
                        server_onupdate=current_time,
                        nullable=False,
                    ),
                )
            }
        )

        for field, field_props in dict(self.context_schema).items():
            if isinstance(field_props, ValueSchemaField) and field not in [
                t.name for t in self.tables[self._CONTEXTS].c
            ]:
                if (
                    field_props.on_read != SchemaFieldReadPolicy.IGNORE
                    or field_props.on_write != SchemaFieldWritePolicy.IGNORE
                ):
                    raise RuntimeError(
                        f"Value field `{field}` is not ignored in the scheme, yet no columns are created for it!"
                    )

        asyncio.run(self._create_self_tables())

    def set_context_schema(self, scheme: ContextSchema):
        super().set_context_schema(scheme)
        self.context_schema.id.on_write = SchemaFieldWritePolicy.UPDATE_ONCE
        self.context_schema.ext_id.on_write = SchemaFieldWritePolicy.UPDATE_ONCE
        self.context_schema.created_at.on_write = SchemaFieldWritePolicy.IGNORE
        self.context_schema.updated_at.on_write = SchemaFieldWritePolicy.IGNORE

    @threadsafe_method
    @cast_key_to_string()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        fields, int_id = await self._read_keys(key)
        if int_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.context_schema.read_context(fields, self._read_ctx, key, int_id)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @cast_key_to_string()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        fields, _ = await self._read_keys(key)
        value_hash = self.hash_storage.get(key, None)
        await self.context_schema.write_context(value, value_hash, fields, self._write_ctx, key)

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: Union[Hashable, str]):
        self.hash_storage[key] = None
        async with self.engine.begin() as conn:
            await conn.execute(
                self.tables[self._CONTEXTS]
                .insert()
                .values({self.context_schema.id.name: None, self.context_schema.ext_id.name: key})
            )

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        stmt = select(self.tables[self._CONTEXTS].c[self.context_schema.id.name])
        stmt = stmt.where(self.tables[self._CONTEXTS].c[self.context_schema.ext_id.name] == key)
        stmt = stmt.order_by(self.tables[self._CONTEXTS].c[self.context_schema.created_at.name].desc())
        async with self.engine.begin() as conn:
            return (await conn.execute(stmt)).fetchone()[0] is not None

    @threadsafe_method
    async def len_async(self) -> int:
        stmt = select(self.tables[self._CONTEXTS].c[self.context_schema.ext_id.name])
        stmt = stmt.where(self.tables[self._CONTEXTS].c[self.context_schema.id.name] != None)  # noqa E711
        stmt = stmt.group_by(self.tables[self._CONTEXTS].c[self.context_schema.ext_id.name])
        stmt = select(func.count()).select_from(stmt.subquery())
        async with self.engine.begin() as conn:
            return (await conn.execute(stmt)).fetchone()[0]

    @threadsafe_method
    async def clear_async(self):
        self.hash_storage = {key: None for key, _ in self.hash_storage.items()}
        async with self.engine.begin() as conn:
            query = select(self.tables[self._CONTEXTS].c[self.context_schema.ext_id.name]).distinct()
            result = (await conn.execute(query)).fetchall()
            if len(result) > 0:
                elements = [
                    dict(**{self.context_schema.id.name: None}, **{self.context_schema.ext_id.name: key[0]})
                    for key in result
                ]
                await conn.execute(self.tables[self._CONTEXTS].insert().values(elements))

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

    # TODO: optimize for PostgreSQL: single query.
    async def _read_keys(self, ext_id: str) -> Tuple[Dict[str, List[str]], Optional[str]]:
        subq = select(self.tables[self._CONTEXTS].c[self.context_schema.id.name])
        subq = subq.where(self.tables[self._CONTEXTS].c[self.context_schema.ext_id.name] == ext_id)
        subq = subq.order_by(self.tables[self._CONTEXTS].c[self.context_schema.created_at.name].desc()).limit(1)
        nested_dict_keys = dict()
        async with self.engine.begin() as conn:
            int_id = (await conn.execute(subq)).fetchone()
            if int_id is None:
                return nested_dict_keys, None
            else:
                int_id = int_id[0]
            mutable_tables_subset = [field for field in self.tables.keys() if field != self._CONTEXTS]
            for field in mutable_tables_subset:
                stmt = select(self.tables[field].c[self._KEY_FIELD])
                stmt = stmt.where(self.tables[field].c[self.context_schema.id.name] == int_id)
                for [key] in (await conn.execute(stmt)).fetchall():
                    if key is not None:
                        if field not in nested_dict_keys:
                            nested_dict_keys[field] = list()
                        nested_dict_keys[field] += [key]
        return nested_dict_keys, int_id

    # TODO: optimize for PostgreSQL: single query.
    async def _read_ctx(self, subscript: Dict[str, Union[bool, Dict[Hashable, bool]]], int_id: str, _: str) -> Dict:
        result_dict = dict()
        async with self.engine.begin() as conn:
            non_empty_value_subset = [
                field for field, value in subscript.items() if isinstance(value, dict) and len(value) > 0
            ]
            for field in non_empty_value_subset:
                keys = [key for key, value in subscript[field].items() if value]
                stmt = select(self.tables[field].c[self._KEY_FIELD], self.tables[field].c[self._VALUE_FIELD])
                stmt = stmt.where(self.tables[field].c[self.context_schema.id.name] == int_id)
                stmt = stmt.where(self.tables[field].c[self._KEY_FIELD].in_(keys))
                for [key, value] in (await conn.execute(stmt)).fetchall():
                    if value is not None:
                        if field not in result_dict:
                            result_dict[field] = dict()
                        result_dict[field][key] = value
            columns = [
                c
                for c in self.tables[self._CONTEXTS].c
                if isinstance(subscript.get(c.name, False), bool) and subscript.get(c.name, False)
            ]
            stmt = select(*columns)
            stmt = stmt.where(self.tables[self._CONTEXTS].c[self.context_schema.id.name] == int_id)
            for [key, value] in zip([c.name for c in columns], (await conn.execute(stmt)).fetchone()):
                if value is not None:
                    result_dict[key] = value
        return result_dict

    async def _write_ctx(self, data: Dict[str, Any], int_id: str, _: str):
        async with self.engine.begin() as conn:
            for field, storage in {k: v for k, v in data.items() if isinstance(v, dict)}.items():
                if len(storage.items()) > 0:
                    values = [
                        {self.context_schema.id.name: int_id, self._KEY_FIELD: key, self._VALUE_FIELD: value}
                        for key, value in storage.items()
                    ]
                    insert_stmt = insert(self.tables[field]).values(values)
                    update_stmt = _get_update_stmt(
                        self.dialect,
                        insert_stmt,
                        [c.name for c in self.tables[field].c],
                        [self.context_schema.id.name, self._KEY_FIELD],
                    )
                    await conn.execute(update_stmt)
            values = {k: v for k, v in data.items() if not isinstance(v, dict)}
            if len(values.items()) > 0:
                insert_stmt = insert(self.tables[self._CONTEXTS]).values(
                    {**values, self.context_schema.id.name: int_id}
                )
                update_stmt = _get_update_stmt(self.dialect, insert_stmt, values.keys(), [self.context_schema.id.name])
                await conn.execute(update_stmt)
