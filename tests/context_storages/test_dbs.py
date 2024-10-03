import os
from platform import system
from socket import AF_INET, SOCK_STREAM, socket
from typing import Any, Optional
import asyncio
import random

import pytest

from chatsky.context_storages import (
    get_protocol_install_suggestion,
    context_storage_factory,
    postgres_available,
    mysql_available,
    sqlite_available,
    redis_available,
    mongo_available,
    ydb_available,
)
from chatsky.utils.testing.cleanup_db import (
    delete_file,
    delete_mongo,
    delete_redis,
    delete_sql,
    delete_ydb,
)
from chatsky.context_storages import DBContextStorage
from chatsky.context_storages.database import FieldConfig
from chatsky import Pipeline, Context, Message
from chatsky.core.context import FrameworkData
from chatsky.utils.context_dict.ctx_dict import ContextDict
from chatsky.utils.testing import TOY_SCRIPT_KWARGS, HAPPY_PATH, check_happy_path

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


@pytest.mark.parametrize(
    ["protocol", "expected"],
    [
        ("pickle", "Try to run `pip install chatsky[pickle]`"),
        ("postgresql", "Try to run `pip install chatsky[postgresql]`"),
        ("false", ""),
    ],
)
def test_protocol_suggestion(protocol: str, expected: str) -> None:
    result = get_protocol_install_suggestion(protocol)
    assert result == expected


@pytest.mark.parametrize(
    "db_kwargs,db_teardown",
    [
        pytest.param({"path": ""}, None, id="memory"),
        pytest.param({"path": "shelve://{__testing_file__}"}, delete_file, id="shelve"),
        pytest.param({"path": "json://{__testing_file__}"}, delete_file, id="json"),
        pytest.param({"path": "pickle://{__testing_file__}"}, delete_file, id="pickle"),
        pytest.param({
            "path": "mongodb://{MONGO_INITDB_ROOT_USERNAME}:{MONGO_INITDB_ROOT_PASSWORD}@"
                    "localhost:27017/{MONGO_INITDB_ROOT_USERNAME}"
        }, delete_mongo, id="mongo", marks=[
            pytest.mark.docker,
            pytest.mark.skipif(not MONGO_ACTIVE, reason="Mongodb server is not running"),
            pytest.mark.skipif(not mongo_available, reason="Mongodb dependencies missing")
        ]),
        pytest.param({"path": "redis://:{REDIS_PASSWORD}@localhost:6379/0"}, delete_redis, id="redis", marks=[
            pytest.mark.docker,
            pytest.mark.skipif(not REDIS_ACTIVE, reason="Redis server is not running"),
            pytest.mark.skipif(not redis_available, reason="Redis dependencies missing")
        ]),
        pytest.param({
            "path": "postgresql+asyncpg://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@localhost:5432/{POSTGRES_DB}"
        }, delete_sql, id="postgres", marks=[
            pytest.mark.docker,
            pytest.mark.skipif(not POSTGRES_ACTIVE, reason="Postgres server is not running"),
            pytest.mark.skipif(not postgres_available, reason="Postgres dependencies missing")
        ]),
        pytest.param({
            "path": "sqlite+aiosqlite:{__separator__}{__testing_file__}"
        }, delete_sql, id="sqlite", marks=[
            pytest.mark.skipif(not sqlite_available, reason="Sqlite dependencies missing")
        ]),
        pytest.param({
            "path": "mysql+asyncmy://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@localhost:3307/{MYSQL_DATABASE}"
        }, delete_sql, id="mysql", marks=[
            pytest.mark.docker,
            pytest.mark.skipif(not MYSQL_ACTIVE, reason="Mysql server is not running"),
            pytest.mark.skipif(not mysql_available, reason="Mysql dependencies missing")
        ]),
        pytest.param({"path": "{YDB_ENDPOINT}{YDB_DATABASE}"}, delete_ydb, id="ydb", marks=[
            pytest.mark.docker,
            pytest.mark.skipif(not YDB_ACTIVE, reason="YQL server not running"),
            pytest.mark.skipif(not ydb_available, reason="YDB dependencies missing")
        ]),
    ]
)
class TestContextStorages:
    @pytest.fixture
    async def db(self, db_kwargs, db_teardown, tmpdir_factory):
        kwargs = {
            "__testing_file__": str(tmpdir_factory.mktemp("data").join("file.db")),
            "__separator__": "///" if system() == "Windows" else "////",
            **os.environ
        }
        db_kwargs["path"] = db_kwargs["path"].format(**kwargs)
        context_storage = context_storage_factory(**db_kwargs)

        yield context_storage

        if db_teardown is not None:
            await db_teardown(context_storage)

    @pytest.fixture
    async def add_context(self, db):
        async def add_context(ctx_id: str):
            await db.update_main_info(ctx_id, 1, 1, 1, b"1")
            await db.update_field_items(ctx_id, "labels", [(0, b"0")])
        yield add_context

    @staticmethod
    def configure_context_storage(
        context_storage: DBContextStorage,
        rewrite_existing: Optional[bool] = None,
        labels_config: Optional[FieldConfig] = None,
        requests_config: Optional[FieldConfig] = None,
        responses_config: Optional[FieldConfig] = None,
        misc_config: Optional[FieldConfig] = None,
        all_config: Optional[FieldConfig] = None,
    ) -> None:
        if rewrite_existing is not None:
            context_storage.rewrite_existing = rewrite_existing
        if all_config is not None:
            labels_config = requests_config = responses_config = misc_config = all_config
        if labels_config is not None:
            context_storage.labels_config = labels_config
        if requests_config is not None:
            context_storage.requests_config = requests_config
        if responses_config is not None:
            context_storage.responses_config = responses_config
        if misc_config is not None:
            context_storage.misc_config = misc_config

    async def test_add_context(self, db, add_context):
        # test the fixture
        await add_context("1")

    async def test_get_main_info(self, db, add_context):
        await add_context("1")
        assert await db.load_main_info("1") == (1, 1, 1, b"1")
        assert await db.load_main_info("2") is None

    async def test_update_main_info(self, db, add_context):
        await add_context("1")
        await add_context("2")
        assert await db.load_main_info("1") == (1, 1, 1, b"1")
        assert await db.load_main_info("2") == (1, 1, 1, b"1")

        await db.update_main_info("1", 2, 1, 3, b"4")
        assert await db.load_main_info("1") == (2, 1, 3, b"4")
        assert await db.load_main_info("2") == (1, 1, 1, b"1")

    async def test_wrong_field_name(self, db):
        with pytest.raises(ValueError, match="Unknown field name"):
            await db.load_field_latest("1", "non-existent")
        with pytest.raises(ValueError, match="Unknown field name"):
            await db.load_field_keys("1", "non-existent")
        with pytest.raises(ValueError, match="Unknown field name"):
            await db.load_field_items("1", "non-existent", {1, 2})
        with pytest.raises(ValueError, match="Unknown field name"):
            await db.update_field_items("1", "non-existent", [(1, b"2")])

    async def test_field_get(self, db, add_context):
        await add_context("1")

        assert await db.load_field_latest("1", "labels") == [(0, b"0")]
        assert await db.load_field_keys("1", "labels") == [0]

        assert await db.load_field_latest("1", "requests") == []
        assert await db.load_field_keys("1", "requests") == []

    async def test_field_update(self, db, add_context):
        await add_context("1")
        assert await db.load_field_latest("1", "labels") == [(0, b"0")]
        assert await db.load_field_latest("1", "requests") == []

        await db.update_field_items("1", "labels", [(0, b"1")])
        await db.update_field_items("1", "requests", [(4, b"4")])
        await db.update_field_items("1", "labels", [(2, b"2")])

        assert await db.load_field_latest("1", "labels") == [(0, b"1"), (2, b"2")]
        assert await db.load_field_keys("1", "labels") == [0, 2]
        assert await db.load_field_latest("1", "requests") == [(4, b"4")]
        assert await db.load_field_keys("1", "requests") == [4]

    async def test_int_key_field_subscript(self, db, add_context):
        await add_context("1")
        await db.update_field_items("1", "requests", [(2, b"2")])
        await db.update_field_items("1", "requests", [(1, b"1")])
        await db.update_field_items("1", "requests", [(0, b"0")])

        self.configure_context_storage(db, requests_config=FieldConfig(name="requests", subscript=2))
        assert await db.load_field_latest("1", "requests") == [(1, b"1"), (2, b"2")]

        self.configure_context_storage(db, requests_config=FieldConfig(name="requests", subscript="__all__"))
        assert await db.load_field_latest("1", "requests") == [(0, b"0"), (1, b"1"), (2, b"2")]

        await db.update_field_items("1", "requests", [(5, b"5")])

        self.configure_context_storage(db, requests_config=FieldConfig(name="requests", subscript=2))
        assert await db.load_field_latest("1", "requests") == [(2, b"2"), (5, b"5")]

    async def test_string_key_field_subscript(self, db, add_context):
        await add_context("1")
        await db.update_field_items("1", "misc", [("4", b"4"), ("0", b"0")])

        self.configure_context_storage(db, misc_config=FieldConfig(name="misc", subscript={"4"}))
        assert await db.load_field_latest("1", "misc") == [("4", b"4")]

        self.configure_context_storage(db, misc_config=FieldConfig(name="misc", subscript="__all__"))
        assert await db.load_field_latest("1", "misc") == [("4", b"4"), ("0", b"0")]

    async def test_delete_field_key(self, db, add_context):
        await add_context("1")

        await db.delete_field_keys("1", "labels", [0])

        assert await db.load_field_latest("1", "labels") == [(0, None)]

    async def test_raises_on_missing_field_keys(self, db, add_context):
        await add_context("1")

        with pytest.raises(KeyError):
            await db.load_field_items("1", "labels", [0, 1])
        with pytest.raises(KeyError):
            await db.load_field_items("1", "requests", [0])

    async def test_delete_context(self, db, add_context):
        await add_context("1")
        await add_context("2")

        # test delete
        await db.delete_context("1")

        assert await db.load_main_info("1") is None
        assert await db.load_main_info("2") == (1, 1, 1, b"1")

        assert await db.load_field_keys("1", "labels") == []
        assert await db.load_field_keys("2", "labels") == [0]

    @pytest.mark.slow
    async def test_concurrent_operations(self, db):
        async def db_operations(key: int):
            str_key = str(key)
            byte_key = bytes(key)
            await asyncio.sleep(random.random() / 100)
            await db.update_main_info(str_key, key, key + 1, key, byte_key)
            await asyncio.sleep(random.random() / 100)
            assert await db.load_main_info(str_key) == (key, key + 1, key, byte_key)

            for idx in range(1, 20):
                await db.update_field_items(str_key, "requests", [(0, bytes(2 * key + idx)), (idx, bytes(key + idx))])
                await asyncio.sleep(random.random() / 100)
                keys = list(range(idx + 1))
                assert await db.load_field_keys(str_key, "requests") == keys
                assert await db.load_field_items(str_key, "requests", keys) == [
                    bytes(2 * key + idx),
                    *[bytes(key + k) for k in range(1, idx + 1)]
                ]

        await asyncio.gather(*(db_operations(key * 2) for key in range(3)))

    async def test_pipeline(self, db) -> None:
        # Test Pipeline workload on DB
        pipeline = Pipeline(**TOY_SCRIPT_KWARGS, context_storage=db)
        check_happy_path(pipeline, happy_path=HAPPY_PATH)
