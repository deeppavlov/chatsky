import os
from platform import system
from socket import AF_INET, SOCK_STREAM, socket
from typing import Any, Optional

import pytest

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
        pytest.param({"path": "shelve://{__testing_file__}"}, delete_shelve, id="shelve"),
        pytest.param({"path": "json://{__testing_file__}"}, delete_json, id="json", marks=[
            pytest.mark.skipif(not json_available, reason="JSON dependencies missing")
        ]),
        pytest.param({"path": "pickle://{__testing_file__}"}, delete_pickle, id="pickle", marks=[
            pytest.mark.skipif(not pickle_available, reason="Pickle dependencies missing")
        ]),
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
    def testing_context(self, context_factory, db) -> Context:
        ctx = context_factory()
        ctx.requests[0] = Message(text="message text")
        ctx.misc["some_key"] = "some_value"
        ctx.misc["other_key"] = "other_value"
        ctx.framework_data.pipeline = None
        ctx._storage = db
        ctx.labels._storage = db
        ctx.labels._field_name = db.labels_config.name
        ctx.requests._storage = db
        ctx.requests._field_name = db.requests_config.name
        ctx.responses._storage = db
        ctx.responses._field_name = db.responses_config.name
        ctx.misc._storage = db
        ctx.misc._field_name = db.misc_config.name
        return ctx

    @staticmethod
    def _setup_context_storage(
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

    async def test_basic(self, db: DBContextStorage, testing_context: Context) -> None:
        # Test nothing exists in database
        nothing = await db.load_main_info(testing_context.id)
        assert nothing is None

        # Test context main info can be stored and loaded
        await db.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at,
                                  testing_context._updated_at,
                                  testing_context.framework_data.model_dump_json().encode())
        turn_id, created_at, updated_at, framework_data = await db.load_main_info(testing_context.id)
        assert testing_context.current_turn_id == turn_id
        assert testing_context._created_at == created_at
        assert testing_context._updated_at == updated_at
        assert testing_context.framework_data == FrameworkData.model_validate_json(framework_data)

        # Test context main info can be updated
        testing_context.framework_data.stats["key"] = "value"
        await db.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at,
                                  testing_context._updated_at,
                                  testing_context.framework_data.model_dump_json().encode())
        turn_id, created_at, updated_at, framework_data = await db.load_main_info(testing_context.id)
        assert testing_context.framework_data == FrameworkData.model_validate_json(framework_data)

        # Test context fields can be stored and loaded
        await db.update_field_items(testing_context.id, db.requests_config.name,
                                    [(k, v.model_dump_json().encode()) for k, v in
                                     await testing_context.requests.items()])
        requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
        assert testing_context.requests == {k: Message.model_validate_json(v) for k, v in requests}

        # Test context fields keys can be loaded
        req_keys = await db.load_field_keys(testing_context.id, db.requests_config.name)
        assert testing_context.requests.keys() == list(req_keys)

        # Test context values can be loaded
        req_vals = await db.load_field_items(testing_context.id, db.requests_config.name, set(req_keys))
        assert await testing_context.requests.values() == [Message.model_validate_json(val) for val in req_vals]

        # Test context values can be updated
        await testing_context.requests.update({0: Message("new message text"), 1: Message("other message text")})
        requests_dump = [(k, v.model_dump_json().encode()) for k, v in await testing_context.requests.items()]
        await db.update_field_items(testing_context.id, db.requests_config.name, requests_dump)
        requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
        req_keys = await db.load_field_keys(testing_context.id, db.requests_config.name)
        req_vals = await db.load_field_items(testing_context.id, db.requests_config.name, set(req_keys))
        assert testing_context.requests == {k: Message.model_validate_json(v) for k, v in requests}
        assert testing_context.requests.keys() == list(req_keys)
        assert await testing_context.requests.values() == [Message.model_validate_json(val) for val in req_vals]

        # Test context values can be deleted
        await db.delete_field_keys(testing_context.id, db.requests_config.name, testing_context.requests.keys())
        requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
        req_keys = await db.load_field_keys(testing_context.id, db.requests_config.name)
        req_vals = await db.load_field_items(testing_context.id, db.requests_config.name, set(req_keys))
        assert {k: None for k in testing_context.requests.keys()} == dict(requests)
        assert testing_context.requests.keys() == list(req_keys)
        assert list() == [Message.model_validate_json(val) for val in req_vals if val is not None]

        # Test context main info can be deleted
        await db.update_field_items(testing_context.id, db.requests_config.name, requests_dump)
        await db.delete_main_info(testing_context.id)
        nothing = await db.load_main_info(testing_context.id)
        requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
        req_keys = await db.load_field_keys(testing_context.id, db.requests_config.name)
        req_vals = await db.load_field_items(testing_context.id, db.requests_config.name, set(req_keys))
        assert nothing is None
        assert dict() == dict(requests)
        assert set() == set(req_keys)
        assert list() == [Message.model_validate_json(val) for val in req_vals]

        # Test all database can be cleared
        await db.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at,
                                  testing_context._updated_at,
                                  testing_context.framework_data.model_dump_json().encode())
        await db.update_field_items(testing_context.id, db.requests_config.name, await testing_context.requests.items())
        await db.clear_all()
        nothing = await db.load_main_info(testing_context.id)
        requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
        req_keys = await db.load_field_keys(testing_context.id, db.requests_config.name)
        req_vals = await db.load_field_items(testing_context.id, db.requests_config.name, set(req_keys))
        assert nothing is None
        assert dict() == dict(requests)
        assert set() == set(req_keys)
        assert list() == [Message.model_validate_json(val) for val in req_vals]

    async def test_partial_storage(self, db: DBContextStorage, testing_context: Context) -> None:
        # Store some data in storage
        await db.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at,
                                  testing_context._updated_at,
                                  testing_context.framework_data.model_dump_json().encode())
        await db.update_field_items(testing_context.id, db.requests_config.name, await testing_context.requests.items())

        # Test getting keys with 0 subscription
        self._setup_context_storage(db, requests_config=FieldConfig(name=db.requests_config.name, subscript="__none__"))
        requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
        assert 0 == len(requests)

        # Test getting keys with standard (3) subscription
        self._setup_context_storage(db, requests_config=FieldConfig(name=db.requests_config.name, subscript=3))
        requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
        assert len(testing_context.requests.keys()) == len(requests)

    async def test_large_misc(self, db: DBContextStorage, testing_context: Context) -> None:
        BIG_NUMBER = 1000

        # Store data main info in storage
        await db.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at,
                                  testing_context._updated_at,
                                  testing_context.framework_data.model_dump_json().encode())

        # Fill context misc with data and store it in database
        testing_context.misc = ContextDict.model_validate({f"key_{i}": f"data number #{i}" for i in range(BIG_NUMBER)})
        await db.update_field_items(testing_context.id, db.misc_config.name, await testing_context.misc.items())

        # Check data keys stored in context
        misc = await db.load_field_keys(testing_context.id, db.misc_config.name)
        assert len(testing_context.misc.keys()) == len(misc)

        # Check data values stored in context
        misc_keys = await db.load_field_keys(testing_context.id, db.misc_config.name)
        misc_vals = await db.load_field_items(testing_context.id, db.misc_config.name, set(misc_keys))
        for k, v in zip(misc_keys, misc_vals):
            assert await testing_context.misc[k] == v

    async def test_many_ctx(self, db: DBContextStorage, testing_context: Context) -> None:
        # Fill database with contexts with one misc value and two requests
        for i in range(1, 101):
            ctx = await Context.connected(db, ("flow", "node"), f"ctx_id_{i}")
            await ctx.misc.update({f"key_{i}": f"ctx misc value {i}"})
            ctx.requests[0] = Message("useful message")
            ctx.requests[i] = Message("some message")
            await ctx.store()
            if i == 1:
                print(ctx._storage._storage[ctx._storage._turns_table_name])

        # Check that both misc and requests are read as expected
        for i in range(1, 101):
            ctx = await Context.connected(db, ("flow", "node"), f"ctx_id_{i}")
            assert await ctx.misc[f"key_{i}"] == f"ctx misc value {i}"
            assert (await ctx.requests[0]).text == "useful message"
            assert (await ctx.requests[i]).text == "some message"

    async def test_integration(self, db: DBContextStorage, testing_context: Context) -> None:
        # Setup context storage for automatic element loading
        self._setup_context_storage(
            db,
            rewrite_existing=True,
            labels_config=FieldConfig(name=db.labels_config.name, subscript="__all__"),
            requests_config=FieldConfig(name=db.requests_config.name, subscript="__all__"),
            responses_config=FieldConfig(name=db.responses_config.name, subscript="__all__"),
            misc_config=FieldConfig(name=db.misc_config.name, subscript="__all__"),
        )

        # Check labels storing, deleting and retrieveing
        await testing_context.labels.store()
        labels = await ContextDict.connected(db, testing_context.id, db.labels_config.name, Message)
        await db.delete_field_keys(testing_context.id, db.labels_config.name,
                                   [str(k) for k in testing_context.labels.keys()])
        assert testing_context.labels == labels

        # Check requests storing, deleting and retrieveing
        await testing_context.requests.store()
        requests = await ContextDict.connected(db, testing_context.id, db.requests_config.name, Message)
        await db.delete_field_keys(testing_context.id, db.requests_config.name,
                                   [str(k) for k in testing_context.requests.keys()])
        assert testing_context.requests == requests

        # Check responses storing, deleting and retrieveing
        await testing_context.responses.store()
        responses = await ContextDict.connected(db, testing_context.id, db.responses_config.name, Message)
        await db.delete_field_keys(testing_context.id, db.responses_config.name,
                                   [str(k) for k in testing_context.responses.keys()])
        assert testing_context.responses == responses

        # Check misc storing, deleting and retrieveing
        await testing_context.misc.store()
        misc = await ContextDict.connected(db, testing_context.id, db.misc_config.name, Any)
        await db.delete_field_keys(testing_context.id, db.misc_config.name,
                                   [f'"{k}"' for k in testing_context.misc.keys()])
        assert testing_context.misc == misc

        # Check whole context storing, deleting and retrieveing
        await testing_context.store()
        context = await Context.connected(db, None, testing_context.id)
        await db.delete_main_info(testing_context.id)
        assert testing_context == context

    async def test_pipeline(self, db: DBContextStorage, testing_context: Context) -> None:
        # Test Pipeline workload on DB
        pipeline = Pipeline(**TOY_SCRIPT_KWARGS, context_storage=db)
        check_happy_path(pipeline, happy_path=HAPPY_PATH)
