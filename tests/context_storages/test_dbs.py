import pytest
import socket
import os
from platform import system

from dff.context_storages import (
    context_storage_factory,
    DBContextStorage,
    get_protocol_install_suggestion,
    JSONContextStorage,
    PickleContextStorage,
    ShelveContextStorage,
    DBAbstractContextStorage,
    SQLContextStorage,
    postgres_available,
    mysql_available,
    sqlite_available,
    RedisContextStorage,
    redis_available,
    MongoContextStorage,
    mongo_available,
    YDBContextStorage,
    ydb_available,
)

from dff.script import Context

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.pipeline import Pipeline
from dff.utils.testing import check_happy_path, TOY_SCRIPT, HAPPY_PATH

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


def ping_localhost(port: int, timeout=60):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", port))
    except OSError:
        return False
    else:
        s.close()
        return True


MONGO_ACTIVE = ping_localhost(27017)

REDIS_ACTIVE = ping_localhost(6379)

POSTGRES_ACTIVE = ping_localhost(5432)

MYSQL_ACTIVE = ping_localhost(3307)

YDB_ACTIVE = ping_localhost(2136)


def generic_test(db, testing_context, context_id):
    assert isinstance(db, DBContextStorage)
    assert isinstance(db, DBAbstractContextStorage)
    # perform cleanup
    db.clear()
    assert len(db) == 0
    # test write operations
    db[context_id] = Context(id=context_id)
    assert context_id in db
    assert len(db) == 1
    db[context_id] = testing_context  # overwriting a key
    assert len(db) == 1
    # test read operations
    new_ctx = db[context_id]
    assert isinstance(new_ctx, Context)
    assert {**new_ctx.dict(), "id": str(new_ctx.id)} == {**testing_context.dict(), "id": str(testing_context.id)}
    # test delete operations
    del db[context_id]
    assert context_id not in db
    # test `get` method
    assert db.get(context_id) is None
    pipeline = Pipeline.from_script(
        TOY_SCRIPT,
        context_storage=db,
        start_label=("greeting_flow", "start_node"),
        fallback_label=("greeting_flow", "fallback_node"),
    )
    check_happy_path(pipeline, happy_path=HAPPY_PATH)


@pytest.mark.parametrize(
    ["protocol", "expected"],
    [
        ("pickle", "Try to run `pip install dff[pickle]`"),
        ("postgresql", "Try to run `pip install dff[postgresql]`"),
        ("false", ""),
    ],
)
def test_protocol_suggestion(protocol, expected):
    result = get_protocol_install_suggestion(protocol)
    assert result == expected


def test_main(testing_file, testing_context, context_id):
    assert issubclass(DBContextStorage, DBAbstractContextStorage)
    db = context_storage_factory(f"json://{testing_file}")
    generic_test(db, testing_context, context_id)


def test_shelve(testing_file, testing_context, context_id):
    db = ShelveContextStorage(f"shelve://{testing_file}")
    generic_test(db, testing_context, context_id)


def test_json(testing_file, testing_context, context_id):
    db = JSONContextStorage(f"json://{testing_file}")
    generic_test(db, testing_context, context_id)


def test_pickle(testing_file, testing_context, context_id):
    db = PickleContextStorage(f"pickle://{testing_file}")
    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(not MONGO_ACTIVE, reason="Mongodb server is not running")
@pytest.mark.skipif(not mongo_available, reason="Mongodb dependencies missing")
def test_mongo(testing_context, context_id):
    if system() == "Windows":
        pytest.skip()

    db = MongoContextStorage(
        "mongodb://{}:{}@localhost:27017/{}".format(
            os.getenv("MONGO_INITDB_ROOT_USERNAME"),
            os.getenv("MONGO_INITDB_ROOT_PASSWORD"),
            os.getenv("MONGO_INITDB_ROOT_USERNAME"),
        )
    )
    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(not REDIS_ACTIVE, reason="Redis server is not running")
@pytest.mark.skipif(not redis_available, reason="Redis dependencies missing")
def test_redis(testing_context, context_id):
    db = RedisContextStorage("redis://{}:{}@localhost:6379/{}".format("", os.getenv("REDIS_PASSWORD"), "0"))
    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(not POSTGRES_ACTIVE, reason="Postgres server is not running")
@pytest.mark.skipif(not postgres_available, reason="Postgres dependencies missing")
def test_postgres(testing_context, context_id):
    db = SQLContextStorage(
        "postgresql://{}:{}@localhost:5432/{}".format(
            os.getenv("POSTGRES_USERNAME"),
            os.getenv("POSTGRES_PASSWORD"),
            os.getenv("POSTGRES_DB"),
        )
    )
    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(not sqlite_available, reason="Sqlite dependencies missing")
def test_sqlite(testing_file, testing_context, context_id):
    separator = "///" if system() == "Windows" else "////"
    db = SQLContextStorage(f"sqlite:{separator}{testing_file}")

    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(not MYSQL_ACTIVE, reason="Mysql server is not running")
@pytest.mark.skipif(not mysql_available, reason="Mysql dependencies missing")
def test_mysql(testing_context, context_id):
    db = SQLContextStorage(
        "mysql+pymysql://{}:{}@localhost:3307/{}".format(
            os.getenv("MYSQL_USERNAME"),
            os.getenv("MYSQL_PASSWORD"),
            os.getenv("MYSQL_DATABASE"),
        )
    )
    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(not YDB_ACTIVE, reason="YQL server not running")
@pytest.mark.skipif(not ydb_available, reason="YDB dependencies missing")
def test_ydb(testing_context, context_id):
    db = YDBContextStorage(
        "{}{}".format(
            os.getenv("YDB_ENDPOINT"),
            os.getenv("YDB_DATABASE"),
        ),
        "test",
    )
    generic_test(db, testing_context, context_id)
