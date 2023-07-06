from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Optional, Union

from sqlalchemy.exc import ArgumentError
from sqlalchemy.engine import create_engine, Engine, Connection
from sqlalchemy.engine.interfaces import _CoreAnyExecuteParams, CoreExecuteOptionsParameter
from sqlalchemy.engine.cursor import CursorResult
from sqlalchemy.engine.url import URL
from sqlalchemy.sql.base import Executable
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection, AsyncTransaction
from sqlalchemy.ext.asyncio.exc import AsyncMethodRequired


class DumperConnection(AsyncConnection):
    def __init__(
        self,
        async_engine: AsyncEngine,
        file_path: Path,
        sync_connection: Optional[Connection] = None,
    ):
        AsyncConnection.__init__(self, async_engine, sync_connection)
        self.operation = None
        self.file = file_path

    def begin(self, operation: Optional[str] = None) -> AsyncTransaction:
        self.operation = operation
        return super().begin()

    async def execute(
        self,
        statement: Executable,
        parameters: Optional[_CoreAnyExecuteParams] = None,
        *args,
        execution_options: Optional[CoreExecuteOptionsParameter] = None,
    ) -> CursorResult[Any]:
        with open(self.file, "a+") as f:
            if self.operation is not None:
                f.write(f"Operation {self.operation.upper()}:\n")
            f.write(f"{statement}\n\n\n")
        return await super().execute(statement, parameters, *args, execution_options=execution_options)


class DumperEngine(AsyncEngine):
    def __init__(self, sync_engine: Engine, file_path: Optional[Union[str, Path]] = None):
        AsyncEngine.__init__(self, sync_engine)
        self.file = Path(file_path if file_path is not None else f"sql-dump-{self.dialect.name}.txt")

    def connect(self) -> DumperConnection:
        return DumperConnection(self, self.file)

    @asynccontextmanager
    async def begin(self, operation: Optional[str] = None) -> AsyncIterator[DumperConnection]:
        async with self.connect() as conn:
            async with conn.begin(operation):
                yield conn


def create_dump_engine(url: Union[str, URL], file_path: Optional[Union[str, Path]] = None, **kw: Any) -> DumperEngine:
    if kw.get("server_side_cursors", False):
        raise AsyncMethodRequired("Can't set server_side_cursors for async engine globally; use the connection.stream() method for an async streaming result set")
    kw["_is_async"] = True
    async_creator = kw.pop("async_creator", None)
    if async_creator:
        if kw.get("creator", None):
            raise ArgumentError("Can only specify one of 'async_creator' or 'creator', not both.")

        def creator() -> Any:
            return sync_engine.dialect.dbapi.connect(async_creator_fn=async_creator)

        kw["creator"] = creator
    sync_engine = create_engine(url, **kw)
    return DumperEngine(sync_engine, file_path)
