from time import sleep
from typing import Dict, Union
from dff.context_storages import DBContextStorage, ALL_ITEMS
from dff.context_storages.context_schema import SchemaField
from dff.pipeline import Pipeline
from dff.script import Context, Message
from dff.utils.testing import TOY_SCRIPT_ARGS, HAPPY_PATH, check_happy_path


def simple_test(db: DBContextStorage, testing_context: Context, context_id: str):
    # Operation WRITE
    db[context_id] = testing_context

    # Operation LENGTH
    assert len(db) == 1

    # Operation CONTAINS
    assert context_id in db

    # Operation READ
    assert db[context_id] is not None

    # Operation DELETE
    del db[context_id]

    # Operation CLEAR
    db.clear()


def basic_test(db: DBContextStorage, testing_context: Context, context_id: str):
    assert len(db) == 0
    assert testing_context.storage_key is None

    # Test write operations
    db[context_id] = Context()
    assert context_id in db
    assert len(db) == 1

    # Here we have to sleep because of timestamp calculations limitations:
    # On some platforms, current time can not be calculated with accuracy less than microsecond,
    # so the contexts added won't be stored in the correct order.
    # We sleep for a microsecond to ensure that new contexts' timestamp will be surely more than
    # the previous ones'.
    sleep(0.001)

    db[context_id] = testing_context  # overwriting a key
    assert len(db) == 1
    assert db.keys() == {context_id}

    # Test read operations
    new_ctx = db[context_id]
    assert isinstance(new_ctx, Context)
    assert new_ctx.model_dump() == testing_context.model_dump()

    # Check storage_key has been set up correctly
    if not isinstance(db, dict):
        assert testing_context.storage_key == new_ctx.storage_key == context_id

    # Test delete operations
    del db[context_id]
    assert context_id not in db

    # Test `get` method
    assert db.get(context_id) is None


def pipeline_test(db: DBContextStorage, _: Context, __: str):
    # Test Pipeline workload on DB
    pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=db)
    check_happy_path(pipeline, happy_path=HAPPY_PATH)


def partial_storage_test(db: DBContextStorage, testing_context: Context, context_id: str):
    # Write and read initial context
    db[context_id] = testing_context
    read_context = db[context_id]
    assert testing_context.model_dump() == read_context.model_dump()

    # Remove key
    del db[context_id]

    # Add key to misc and request to requests
    read_context.misc.update(new_key="new_value")
    for i in range(1, 5):
        read_context.add_request(Message(text=f"new message: {i}"))
    write_context = read_context.model_dump()

    # Patch context to use with dict context storage, that doesn't follow read limits
    if not isinstance(db, dict):
        for i in sorted(write_context["requests"].keys())[:-3]:
            del write_context["requests"][i]

    # Write and read updated context
    db[context_id] = read_context
    read_context = db[context_id]
    assert write_context == read_context.model_dump()


def midair_subscript_change_test(db: DBContextStorage, testing_context: Context, context_id: str):
    # Set all appended request to be written
    db.context_schema.append_single_log = False

    # Add new requests to context
    for i in range(1, 10):
        testing_context.add_request(Message(text=f"new message: {i}"))

    # Make read limit larger (7)
    db[context_id] = testing_context
    db.context_schema.requests.subscript = 7

    # Create a copy of context that simulates expected read value (last 7 requests)
    write_context = testing_context.model_dump()
    for i in sorted(write_context["requests"].keys())[:-7]:
        del write_context["requests"][i]

    # Check that expected amount of requests was read only
    read_context = db[context_id]
    assert write_context == read_context.model_dump()

    # Make read limit smaller (2)
    db.context_schema.requests.subscript = 2

    # Create a copy of context that simulates expected read value (last 2 requests)
    write_context = testing_context.model_dump()
    for i in sorted(write_context["requests"].keys())[:-2]:
        del write_context["requests"][i]

    # Check that expected amount of requests was read only
    read_context = db[context_id]
    assert write_context == read_context.model_dump()


def large_misc_test(db: DBContextStorage, testing_context: Context, context_id: str):
    # Fill context misc with data
    for i in range(100000):
        testing_context.misc[f"key_{i}"] = f"data number #{i}"
    db[context_id] = testing_context

    # Check data stored in context
    new_context = db[context_id]
    assert len(new_context.misc) == len(testing_context.misc)
    for i in range(100000):
        assert new_context.misc[f"key_{i}"] == f"data number #{i}"


def many_ctx_test(db: DBContextStorage, _: Context, context_id: str):
    # Set all appended request to be written
    db.context_schema.append_single_log = False

    # Setup schema so that only last request will be written to database
    db.context_schema.requests.subscript = 1

    # Fill database with contexts with one misc value and two requests
    for i in range(1, 101):
        db[f"{context_id}_{i}"] = Context(
            misc={f"key_{i}": f"ctx misc value {i}"},
            requests={0: Message(text="useful message"), i: Message(text="some message")},
        )
        sleep(0.001)

    # Setup schema so that all requests will be read from database
    db.context_schema.requests.subscript = ALL_ITEMS

    # Check database length
    assert len(db) == 100

    # Check that both misc and requests are read as expected
    for i in range(1, 101):
        read_ctx = db[f"{context_id}_{i}"]
        assert read_ctx.misc[f"key_{i}"] == f"ctx misc value {i}"
        assert read_ctx.requests[0].text == "useful message"
        assert read_ctx.requests[i].text == "some message"

    # Check clear
    db.clear()
    assert len(db) == 0


def keys_test(db: DBContextStorage, testing_context: Context, context_id: str):
    # Fill database with contexts
    for i in range(1, 11):
        db[f"{context_id}_{i}"] = Context()
        sleep(0.001)

    # Add and delete a context
    db[context_id] = testing_context
    del db[context_id]

    # Check database keys
    keys = db.keys()
    assert len(keys) == 10
    for i in range(1, 11):
        assert f"{context_id}_{i}" in keys


def single_log_test(db: DBContextStorage, testing_context: Context, context_id: str):
    # Set only one request to be included into CONTEXTS table
    db.context_schema.requests.subscript = 1

    # Add new requestgs to context
    for i in range(1, 10):
        testing_context.add_request(Message(text=f"new message: {i}"))
    db[context_id] = testing_context

    # Setup schema so that all requests will be read from database
    db.context_schema.requests.subscript = ALL_ITEMS

    # Read context and check only the two last context was read - one from LOGS, one from CONTEXT
    read_context = db[context_id]
    assert len(read_context.requests) == 2
    assert read_context.requests[8] == testing_context.requests[8]
    assert read_context.requests[9] == testing_context.requests[9]


simple_test.no_dict = False
basic_test.no_dict = False
pipeline_test.no_dict = False
partial_storage_test.no_dict = False
midair_subscript_change_test.no_dict = True
large_misc_test.no_dict = False
many_ctx_test.no_dict = True
keys_test.no_dict = False
single_log_test.no_dict = True
_TEST_FUNCTIONS = [
    simple_test,
    basic_test,
    pipeline_test,
    partial_storage_test,
    midair_subscript_change_test,
    large_misc_test,
    many_ctx_test,
    keys_test,
    single_log_test,
]


def run_all_functions(db: Union[DBContextStorage, Dict], testing_context: Context, context_id: str):
    frozen_ctx = testing_context.model_dump_json()
    for test in _TEST_FUNCTIONS:
        if isinstance(db, DBContextStorage):
            db.context_schema.append_single_log = True
            db.context_schema.duplicate_context_in_logs = False
            for field_props in [value for value in dict(db.context_schema).values() if isinstance(value, SchemaField)]:
                field_props.subscript = 3
        if not (getattr(test, "no_dict", False) and isinstance(db, dict)):
            if isinstance(db, dict):
                db.clear()
            else:
                db.clear(prune_history=True)
            test(db, Context.cast(frozen_ctx), context_id)
