from dff.context_storages import DBContextStorage
from dff.pipeline import Pipeline
from dff.script import Context, Message
from dff.utils.testing import TOY_SCRIPT_ARGS, HAPPY_PATH, check_happy_path


def generic_test(db: DBContextStorage, testing_context: Context, context_id: str):
    # Perform cleanup
    db.clear()
    assert len(db) == 0

    # Test write operations
    db[context_id] = Context()
    assert context_id in db
    assert len(db) == 1
    db[context_id] = testing_context  # overwriting a key
    assert len(db) == 1

    # Test read operations
    new_ctx = db[context_id]
    assert isinstance(new_ctx, Context)
    assert new_ctx.dict() == testing_context.dict()

    # Test delete operations
    del db[context_id]
    assert context_id not in db

    # Test `get` method
    assert db.get(context_id) is None
    pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=db)
    check_happy_path(pipeline, happy_path=HAPPY_PATH)


def operational_test(db: DBContextStorage, testing_context: Context, context_id: str):
    # Perform cleanup
    db.clear()

    # Write and read initial context
    db[context_id] = testing_context
    read_context = db[context_id]
    assert testing_context.dict() == read_context.dict()

    # Remove key
    del db[context_id]

    # Add key to misc and request to requests
    read_context.misc.update(new_key="new_value")
    read_context.add_request(Message(text="new message"))
    write_context = read_context.dict()

    # Write and read updated context
    db[context_id] = read_context
    read_context = db[context_id]
    assert write_context == read_context.dict()


TEST_FUNCTIONS = [generic_test, operational_test]
