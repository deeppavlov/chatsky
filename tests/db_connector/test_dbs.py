import pytest
import socket
import os
import random
import uuid
import importlib
from platform import system

from dff.core.engine.core import Actor

from dff.connectors.db.protocol import get_protocol_install_suggestion
from dff.connectors.db.json_connector import JSONConnector
from dff.connectors.db.pickle_connector import PickleConnector
from dff.connectors.db.shelve_connector import ShelveConnector
from dff.connectors.db.db_connector import DBAbstractConnector
from dff.connectors.db.sql_connector import SQLConnector, postgres_available, mysql_available, sqlite_available
from dff.connectors.db.redis_connector import RedisConnector, redis_available
from dff.connectors.db.mongo_connector import MongoConnector, mongo_available
from dff.connectors.db.ydb_connector import YDBConnector, ydb_available
from dff.connectors.db import connector_factory


from dff.core.engine.core import Context

from dff.connectors.db import DBConnector
import tests.utils as utils

dot_path_to_addon = utils.get_dot_path_from_tests_to_current_dir(__file__)
db_connector_utils = importlib.import_module(f"examples.{dot_path_to_addon}._db_connector_utils")


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


def run_turns_test(actor: Actor, db: DBConnector):
    for user_id in [str(random.randint(0, 10000000)), random.randint(0, 10000000), uuid.uuid4()]:
        for turn_id, (request, true_response) in enumerate(db_connector_utils.testing_dialog):
            try:
                ctx = db.get(user_id, Context(id=user_id))
                ctx.add_request(request)
                ctx = actor(ctx)
                out_response = ctx.last_response
                db[user_id] = ctx
            except Exception as exc:
                msg = f"user_id={user_id}"
                msg += f" turn_id={turn_id}"
                msg += f" request={request} "
                raise Exception(msg) from exc
            if true_response != out_response:
                msg = f"user_id={user_id}"
                msg += f" turn_id={turn_id}"
                msg += f" request={request} "
                msg += f"\ntrue_response != out_response: "
                msg += f"\n{true_response} != {out_response}"
                raise Exception(msg)


def generic_test(db, testing_context, context_id):
    assert isinstance(db, DBConnector)
    assert isinstance(db, DBAbstractConnector)
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
    actor = Actor(
        db_connector_utils.script,
        start_label=("greeting_flow", "start_node"),
        fallback_label=("greeting_flow", "fallback_node"),
    )
    run_turns_test(actor, db)


@pytest.mark.parametrize(["protocol", "expected"], [
    ("pickle", "Try to run `pip install dff[pickle]`"),
    ("postgresql", "Try to run `pip install dff[postgresql]`"),
    ("false", "")
])
def test_protocol_suggestion(protocol, expected):
    result = get_protocol_install_suggestion(protocol)
    assert result == expected


def test_main(testing_file, testing_context, context_id):
    assert issubclass(DBConnector, DBAbstractConnector)
    db = connector_factory(f"json://{testing_file}")
    generic_test(db, testing_context, context_id)


def test_shelve(testing_file, testing_context, context_id):
    db = ShelveConnector(f"shelve://{testing_file}")
    generic_test(db, testing_context, context_id)


def test_json(testing_file, testing_context, context_id):
    db = JSONConnector(f"json://{testing_file}")
    generic_test(db, testing_context, context_id)


def test_pickle(testing_file, testing_context, context_id):
    db = PickleConnector(f"pickle://{testing_file}")
    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(MONGO_ACTIVE == False, reason="Mongodb server is not running")
@pytest.mark.skipif(mongo_available == False, reason="Mongodb dependencies missing")
def test_mongo(testing_context, context_id):
    if system() == "Windows":
        pytest.skip()

    db = MongoConnector(
        "mongodb://{}:{}@localhost:27017/{}".format(
            os.getenv("MONGO_INITDB_ROOT_USERNAME"),
            os.getenv("MONGO_INITDB_ROOT_PASSWORD"),
            os.getenv("MONGO_INITDB_ROOT_USERNAME"),
        )
    )
    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(REDIS_ACTIVE == False, reason="Redis server is not running")
@pytest.mark.skipif(redis_available == False, reason="Redis dependencies missing")
def test_redis(testing_context, context_id):
    db = RedisConnector("redis://{}:{}@localhost:6379/{}".format("", os.getenv("REDIS_PASSWORD"), "0"))
    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(POSTGRES_ACTIVE == False, reason="Postgres server is not running")
@pytest.mark.skipif(postgres_available == False, reason="Postgres dependencies missing")
def test_postgres(testing_context, context_id):
    db = SQLConnector(
        "postgresql://{}:{}@localhost:5432/{}".format(
            os.getenv("POSTGRES_USERNAME"),
            os.getenv("POSTGRES_PASSWORD"),
            os.getenv("POSTGRES_DB"),
        )
    )
    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(sqlite_available == False, reason="Sqlite dependencies missing")
def test_sqlite(testing_file, testing_context, context_id):
    separator = "///" if system() == "Windows" else "////"
    db = SQLConnector(f"sqlite:{separator}{testing_file}")

    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(MYSQL_ACTIVE == False, reason="Mysql server is not running")
@pytest.mark.skipif(mysql_available == False, reason="Mysql dependencies missing")
def test_mysql(testing_context, context_id):
    db = SQLConnector(
        "mysql+pymysql://{}:{}@localhost:3307/{}".format(
            os.getenv("MYSQL_USERNAME"),
            os.getenv("MYSQL_PASSWORD"),
            os.getenv("MYSQL_DATABASE"),
        )
    )
    generic_test(db, testing_context, context_id)


@pytest.mark.skipif(YDB_ACTIVE == False, reason="YQL server not running")
@pytest.mark.skipif(ydb_available == False, reason="YDB dependencies missing")
def test_ydb(testing_context, context_id):
    db = YDBConnector(
        "{}{}".format(
            os.getenv("YDB_ENDPOINT"),
            os.getenv("YDB_DATABASE"),
        ),
        "test",
    )
    generic_test(db, testing_context, context_id)
