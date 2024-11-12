"""
Yandex DB
---------
The Yandex DB module provides a version of the :py:class:`.DBContextStorage` class that designed to work with
Yandex and other databases. Yandex DataBase is a fully-managed cloud-native SQL service that makes it easy to set up,
operate, and scale high-performance and high-availability databases for your applications.

The Yandex DB module uses the Yandex Cloud SDK, which is a python library that allows you to work
with Yandex Cloud services using python. This allows Chatsky to easily integrate with the Yandex DataBase and
take advantage of the scalability and high-availability features provided by the service.
"""

from asyncio import gather, run
from os.path import join
from typing import Any, Awaitable, Callable, Dict, Set, Tuple, List, Optional, Union
from urllib.parse import urlsplit

from .database import ContextIdFilter, DBContextStorage, _SUBSCRIPT_DICT
from .protocol import get_protocol_install_suggestion

try:
    from ydb import (
        SerializableReadWrite,
        SchemeError,
        TableDescription,
        Column,
        OptionalType,
        PrimitiveType,
    )
    from ydb.aio import Driver, SessionPool
    from ydb.table import Session

    ydb_available = True
except ImportError:
    ydb_available = False


class YDBContextStorage(DBContextStorage):
    """
    Version of the :py:class:`.DBContextStorage` for YDB.

    CONTEXT table is represented by `contexts` table.
    Columns of the table are: active_ctx, id, storage_key, data, created_at and updated_at.

    LOGS table is represented by `logs` table.
    Columns of the table are: id, field, key, value and updated_at.

    :param path: Standard sqlalchemy URI string. One of `grpc` or `grpcs` can be chosen as a protocol.
        Example: `grpc://localhost:2134/local`.
        NB! Do not forget to provide credentials in environmental variables
        or set `YDB_ANONYMOUS_CREDENTIALS` variable to `1`!
    :param context_schema: Context schema for this storage.
    :param serializer: Serializer that will be used for serializing contexts.
    :param table_name_prefix: "namespace" prefix for the two tables created for context storing.
    :param table_name: The name of the table to use.
    """

    _UPDATE_TIME_GREATER_VAR = "update_time_greater"
    _UPDATE_TIME_LESS_VAR = "update_time_less"

    is_asynchronous = True

    def __init__(
        self,
        path: str,
        rewrite_existing: bool = False,
        configuration: Optional[_SUBSCRIPT_DICT] = None,
        table_name_prefix: str = "chatsky_table",
        timeout: int = 5,
    ):
        DBContextStorage.__init__(self, path, rewrite_existing, configuration)

        protocol, netloc, self.database, _, _ = urlsplit(path)
        if not ydb_available:
            install_suggestion = get_protocol_install_suggestion("grpc")
            raise ImportError("`ydb` package is missing.\n" + install_suggestion)

        self.table_prefix = table_name_prefix
        run(self._init_drive(timeout, f"{protocol}://{netloc}"))

    async def _init_drive(self, timeout: int, endpoint: str) -> None:
        self._driver = Driver(endpoint=endpoint, database=self.database)
        client_settings = self._driver.table_client._table_client_settings.with_allow_truncated_result(True)
        self._driver.table_client._table_client_settings = client_settings
        await self._driver.wait(fail_fast=True, timeout=timeout)

        self.pool = SessionPool(self._driver, size=10)

        self.main_table = f"{self.table_prefix}_{self._main_table_name}"
        if not await self._does_table_exist(self.main_table):
            await self._create_main_table(self.main_table)

        self.turns_table = f"{self.table_prefix}_{self._turns_table_name}"
        if not await self._does_table_exist(self.turns_table):
            await self._create_turns_table(self.turns_table)

    async def _does_table_exist(self, table_name: str) -> bool:
        async def callee(session: Session) -> None:
            await session.describe_table(join(self.database, table_name))

        try:
            await self.pool.retry_operation(callee)
            return True
        except SchemeError:
            return False

    async def _create_main_table(self, table_name: str) -> None:
        async def callee(session: Session) -> None:
            await session.create_table(
                "/".join([self.database, table_name]),
                TableDescription()
                .with_column(Column(self._id_column_name, PrimitiveType.Utf8))
                .with_column(Column(self._current_turn_id_column_name, PrimitiveType.Uint64))
                .with_column(Column(self._created_at_column_name, PrimitiveType.Uint64))
                .with_column(Column(self._updated_at_column_name, PrimitiveType.Uint64))
                .with_column(Column(self._misc_column_name, PrimitiveType.String))
                .with_column(Column(self._framework_data_column_name, PrimitiveType.String))
                .with_primary_key(self._id_column_name)
            )

        await self.pool.retry_operation(callee)

    async def _create_turns_table(self, table_name: str) -> None:
        async def callee(session: Session) -> None:
            await session.create_table(
                "/".join([self.database, table_name]),
                TableDescription()
                .with_column(Column(self._id_column_name, PrimitiveType.Utf8))
                .with_column(Column(self._key_column_name, PrimitiveType.Uint32))
                .with_column(Column(self._labels_field_name, OptionalType(PrimitiveType.String)))
                .with_column(Column(self._requests_field_name, OptionalType(PrimitiveType.String)))
                .with_column(Column(self._responses_field_name, OptionalType(PrimitiveType.String)))
                .with_primary_keys(self._id_column_name, self._key_column_name)
            )

        await self.pool.retry_operation(callee)

    @DBContextStorage._convert_id_filter
    async def get_context_ids(self, filter: Union[ContextIdFilter, Dict[str, Any]]) -> Set[str]:
        async def callee(session: Session) -> Set[str]:
            declare, prepare, conditions = list(), dict(), list()
            if filter.update_time_greater is not None:
                declare += [f"DECLARE ${self._UPDATE_TIME_GREATER_VAR} AS Uint64;"]
                prepare.update({f"${self._UPDATE_TIME_GREATER_VAR}": filter.update_time_greater})
                conditions += [f"{self._updated_at_column_name} > ${self._UPDATE_TIME_GREATER_VAR}"]
            if filter.update_time_less is not None:
                declare += [f"DECLARE ${self._UPDATE_TIME_LESS_VAR} AS Uint64;"]
                prepare.update({f"${self._UPDATE_TIME_LESS_VAR}": filter.update_time_less})
                conditions += [f"{self._updated_at_column_name} < ${self._UPDATE_TIME_LESS_VAR}"]
            if len(filter.origin_interface_whitelist) > 0:
                # TODO: implement whitelist once context ID is ready
                pass
            where =  f"WHERE {' AND '.join(conditions)}" if len(conditions) > 0 else ""
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                {" ".join(declare)}
                SELECT {self._id_column_name}
                FROM {self.main_table}
                {where};
                """  # noqa: E501
            result_sets = await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query), prepare, commit_tx=True
            )
            return {e[self._id_column_name] for e in result_sets[0].rows} if len(result_sets[0].rows) > 0 else set()

        return await self.pool.retry_operation(callee)

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes, bytes]]:
        async def callee(session: Session) -> Optional[Tuple[int, int, int, bytes, bytes]]:
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                SELECT {self._current_turn_id_column_name}, {self._created_at_column_name}, {self._updated_at_column_name}, {self._misc_column_name}, {self._framework_data_column_name}
                FROM {self.main_table}
                WHERE {self._id_column_name} = "{ctx_id}";
                """  # noqa: E501
            result_sets = await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query), dict(), commit_tx=True
            )
            return (
                result_sets[0].rows[0][self._current_turn_id_column_name],
                result_sets[0].rows[0][self._created_at_column_name],
                result_sets[0].rows[0][self._updated_at_column_name],
                result_sets[0].rows[0][self._misc_column_name],
                result_sets[0].rows[0][self._framework_data_column_name],
            ) if len(result_sets[0].rows) > 0 else None

        return await self.pool.retry_operation(callee)

    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, misc: bytes, fw_data: bytes) -> None:
        async def callee(session: Session) -> None:
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                DECLARE ${self._current_turn_id_column_name} AS Uint64;
                DECLARE ${self._created_at_column_name} AS Uint64;
                DECLARE ${self._updated_at_column_name} AS Uint64;
                DECLARE ${self._misc_column_name} AS String;
                DECLARE ${self._framework_data_column_name} AS String;
                UPSERT INTO {self.main_table} ({self._id_column_name}, {self._current_turn_id_column_name}, {self._created_at_column_name}, {self._updated_at_column_name}, {self._misc_column_name}, {self._framework_data_column_name})
                VALUES ("{ctx_id}", ${self._current_turn_id_column_name}, ${self._created_at_column_name}, ${self._updated_at_column_name}, ${self._misc_column_name}, ${self._framework_data_column_name});
                """  # noqa: E501
            await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query),
                {
                    f"${self._current_turn_id_column_name}": turn_id,
                    f"${self._created_at_column_name}": crt_at,
                    f"${self._updated_at_column_name}": upd_at,
                    f"${self._misc_column_name}": misc,
                    f"${self._framework_data_column_name}": fw_data,
                },
                commit_tx=True
            )

        await self.pool.retry_operation(callee)

    async def delete_context(self, ctx_id: str) -> None:
        def construct_callee(table_name: str) -> Callable[[Session], Awaitable[None]]:
            async def callee(session: Session) -> None:
                query = f"""
                    PRAGMA TablePathPrefix("{self.database}");
                    DELETE FROM {table_name}
                    WHERE {self._id_column_name} = "{ctx_id}";
                    """  # noqa: E501
                await session.transaction(SerializableReadWrite()).execute(
                    await session.prepare(query), dict(), commit_tx=True
                )

            return callee

        await gather(
            self.pool.retry_operation(construct_callee(self.main_table)),
            self.pool.retry_operation(construct_callee(self.turns_table))
        )

    @DBContextStorage._verify_field_name
    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[int, bytes]]:
        async def callee(session: Session) -> List[Tuple[int, bytes]]:
            limit, key = "", ""
            if isinstance(self._subscripts[field_name], int):
                limit = f"LIMIT {self._subscripts[field_name]}"
            elif isinstance(self._subscripts[field_name], Set):
                keys = ", ".join([str(e) for e in self._subscripts[field_name]])
                key = f"AND {self._key_column_name} IN ({keys})"
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                SELECT {self._key_column_name}, {field_name}
                FROM {self.turns_table}
                WHERE {self._id_column_name} = "{ctx_id}" AND {field_name} IS NOT NULL {key}
                ORDER BY {self._key_column_name} DESC {limit};
                """  # noqa: E501
            result_sets = await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query), dict(), commit_tx=True
            )
            return [
                (e[self._key_column_name], e[field_name]) for e in result_sets[0].rows
            ] if len(result_sets[0].rows) > 0 else list()

        return await self.pool.retry_operation(callee)

    @DBContextStorage._verify_field_name
    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[int]:
        async def callee(session: Session) -> List[int]:
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                SELECT {self._key_column_name}
                FROM {self.turns_table}
                WHERE {self._id_column_name} = "{ctx_id}" AND {field_name} IS NOT NULL;
                """  # noqa: E501
            result_sets = await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query), dict(), commit_tx=True
            )
            return [
                e[self._key_column_name] for e in result_sets[0].rows
            ] if len(result_sets[0].rows) > 0 else list()

        return await self.pool.retry_operation(callee)

    @DBContextStorage._verify_field_name
    async def load_field_items(self, ctx_id: str, field_name: str, keys: List[int]) -> List[Tuple[int, bytes]]:
        async def callee(session: Session) -> List[Tuple[int, bytes]]:
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                SELECT {self._key_column_name}, {field_name}
                FROM {self.turns_table}
                WHERE {self._id_column_name} = "{ctx_id}" AND {field_name} IS NOT NULL
                AND {self._key_column_name} IN ({', '.join([str(e) for e in keys])});
                """  # noqa: E501
            result_sets = await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query), dict(), commit_tx=True
            )
            return [
                (e[self._key_column_name], e[field_name]) for e in result_sets[0].rows
            ] if len(result_sets[0].rows) > 0 else list()

        return await self.pool.retry_operation(callee)

    @DBContextStorage._verify_field_name
    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[int, bytes]]) -> None:
        if len(items) == 0:
            return

        async def callee(session: Session) -> None:
            keys = [str(k) for k, _ in items]
            placeholders = {k: f"${field_name}_{i}" for i, (k, v) in enumerate(items) if v is not None}
            declarations = "\n".join(f"DECLARE {p} AS String;" for p in placeholders.values())
            values = ", ".join(f"(\"{ctx_id}\", {keys[i]}, {placeholders.get(k, 'NULL')})" for i, (k, _) in enumerate(items))
            query = f"""
                PRAGMA TablePathPrefix("{self.database}");
                {declarations}
                UPSERT INTO {self.turns_table} ({self._id_column_name}, {self._key_column_name}, {field_name})
                VALUES {values};
                """  # noqa: E501
            await session.transaction(SerializableReadWrite()).execute(
                await session.prepare(query),
                {placeholders[k]: v for k, v in items if k in placeholders.keys()},
                commit_tx=True
            )

        await self.pool.retry_operation(callee)

    async def clear_all(self) -> None:
        def construct_callee(table_name: str) -> Callable[[Session], Awaitable[None]]:
            async def callee(session: Session) -> None:
                query = f"""
                    PRAGMA TablePathPrefix("{self.database}");
                    DELETE FROM {table_name};
                    """  # noqa: E501
                await session.transaction(SerializableReadWrite()).execute(
                    await session.prepare(query), dict(), commit_tx=True
                )

            return callee

        await gather(
            self.pool.retry_operation(construct_callee(self.main_table)),
            self.pool.retry_operation(construct_callee(self.turns_table))
        )
