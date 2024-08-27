from os import environ
from platform import system
from socket import AF_INET, SOCK_STREAM, socket

import pytest

from chatsky.script.core.context import Context
from chatsky.context_storages import (
    get_protocol_install_suggestion,
    context_storage_factory,
    json_available,
    pickle_available,
    postgres_available,
    mysql_available,
    sqlite_available,
    redis_available,
    mongo_available,
    ydb_available,
    MemoryContextStorage,
)
from chatsky.utils.testing.cleanup_db import (
    delete_shelve,
    delete_json,
    delete_pickle,
    delete_mongo,
    delete_redis,
    delete_sql,
    delete_ydb,
)

from tests.context_storages.test_functions import run_all_functions
from tests.test_utils import get_path_from_tests_to_current_dir

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


def ping_localhost(port: int, timeout: int = 60) -> bool:
    try:
        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(("localhost", port))
    except OSError:
        return False
    else:
        sock.close()
        return True


MONGO_ACTIVE = ping_localhost(27017)

REDIS_ACTIVE = ping_localhost(6379)

POSTGRES_ACTIVE = ping_localhost(5432)

MYSQL_ACTIVE = ping_localhost(3307)

YDB_ACTIVE = ping_localhost(2136)


class TestContextStorages:
    @pytest.mark.parametrize(
        ["protocol", "expected"],
        [
            ("pickle", "Try to run `pip install chatsky[pickle]`"),
            ("postgresql", "Try to run `pip install chatsky[postgresql]`"),
            ("false", ""),
        ],
    )
    def test_protocol_suggestion(self, protocol: str, expected: str) -> None:
        result = get_protocol_install_suggestion(protocol)
        assert result == expected

    @pytest.mark.asyncio
    async def test_memory(self, testing_context: Context) -> None:
        await run_all_functions(MemoryContextStorage(), testing_context)

    @pytest.mark.asyncio
    async def test_shelve(self, testing_file: str, testing_context: Context) -> None:
        db = context_storage_factory(f"shelve://{testing_file}")
        await run_all_functions(db, testing_context)
        await delete_shelve(db)

    @pytest.mark.asyncio
    @pytest.mark.skipif(not json_available, reason="JSON dependencies missing")
    async def test_json(self, testing_file: str, testing_context: Context) -> None:
        db = context_storage_factory(f"json://{testing_file}")
        await run_all_functions(db, testing_context)
        await delete_json(db)

    @pytest.mark.asyncio
    @pytest.mark.skipif(not pickle_available, reason="Pickle dependencies missing")
    async def test_pickle(self, testing_file: str, testing_context: Context) -> None:
        db = context_storage_factory(f"pickle://{testing_file}")
        await run_all_functions(db, testing_context)
        await delete_pickle(db)

    @pytest.mark.docker
    @pytest.mark.asyncio
    @pytest.mark.skipif(not MONGO_ACTIVE, reason="Mongodb server is not running")
    @pytest.mark.skipif(not mongo_available, reason="Mongodb dependencies missing")
    async def test_mongo(self, testing_context: Context) -> None:
        if system() == "Windows":
            pytest.skip()

        db = context_storage_factory(
            "mongodb://{}:{}@localhost:27017/{}".format(
                environ["MONGO_INITDB_ROOT_USERNAME"],
                environ["MONGO_INITDB_ROOT_PASSWORD"],
                environ["MONGO_INITDB_ROOT_USERNAME"],
            )
        )
        await run_all_functions(db, testing_context)
        await delete_mongo(db)

    @pytest.mark.docker
    @pytest.mark.asyncio
    @pytest.mark.skipif(not REDIS_ACTIVE, reason="Redis server is not running")
    @pytest.mark.skipif(not redis_available, reason="Redis dependencies missing")
    async def test_redis(self, testing_context: Context) -> None:
        db = context_storage_factory("redis://{}:{}@localhost:6379/{}".format("", environ["REDIS_PASSWORD"], "0"))
        await run_all_functions(db, testing_context)
        await delete_redis(db)

    @pytest.mark.docker
    @pytest.mark.asyncio
    @pytest.mark.skipif(not POSTGRES_ACTIVE, reason="Postgres server is not running")
    @pytest.mark.skipif(not postgres_available, reason="Postgres dependencies missing")
    async def test_postgres(self, testing_context: Context) -> None:
        db = context_storage_factory(
            "postgresql+asyncpg://{}:{}@localhost:5432/{}".format(
                environ["POSTGRES_USERNAME"],
                environ["POSTGRES_PASSWORD"],
                environ["POSTGRES_DB"],
            )
        )
        await run_all_functions(db, testing_context)
        await delete_sql(db)

    @pytest.mark.asyncio
    @pytest.mark.skipif(not sqlite_available, reason="Sqlite dependencies missing")
    async def test_sqlite(self, testing_file: str, testing_context: Context) -> None:
        separator = "///" if system() == "Windows" else "////"
        db = context_storage_factory(f"sqlite+aiosqlite:{separator}{testing_file}")
        await run_all_functions(db, testing_context)
        await delete_sql(db)

    @pytest.mark.docker
    @pytest.mark.asyncio
    @pytest.mark.skipif(not MYSQL_ACTIVE, reason="Mysql server is not running")
    @pytest.mark.skipif(not mysql_available, reason="Mysql dependencies missing")
    async def test_mysql(self, testing_context) -> None:
        db = context_storage_factory(
            "mysql+asyncmy://{}:{}@localhost:3307/{}".format(
                environ["MYSQL_USERNAME"],
                environ["MYSQL_PASSWORD"],
                environ["MYSQL_DATABASE"],
            )
        )
        await run_all_functions(db, testing_context)
        await delete_sql(db)

    @pytest.mark.docker
    @pytest.mark.asyncio
    @pytest.mark.skipif(not YDB_ACTIVE, reason="YQL server not running")
    @pytest.mark.skipif(not ydb_available, reason="YDB dependencies missing")
    async def test_ydb(self, testing_context: Context) -> None:
        db = context_storage_factory(
            "{}{}".format(
                environ["YDB_ENDPOINT"],
                environ["YDB_DATABASE"],
            ),
            table_name_prefix="test_chatsky_table",
        )
        await run_all_functions(db, testing_context)
        await delete_ydb(db)
