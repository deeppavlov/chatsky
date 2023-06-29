from dff.context_storages import DBContextStorage, ALL_ITEMS
from dff.pipeline import Pipeline
from dff.script import Context, Message
from dff.utils.testing import TOY_SCRIPT_ARGS, HAPPY_PATH, check_happy_path


def basic_test(db: DBContextStorage, testing_context: Context, context_id: str):
    assert len(db) == 0
    assert testing_context.storage_key is None

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

    # Check storage_key has been set up correctly
    if not isinstance(db, dict):
        assert testing_context.storage_key == new_ctx.storage_key == context_id

    # Test delete operations
    del db[context_id]
    assert context_id not in db

    # Test `get` method
    assert db.get(context_id) is None
    pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=db)
    check_happy_path(pipeline, happy_path=HAPPY_PATH)


def partial_storage_test(db: DBContextStorage, testing_context: Context, context_id: str):
    # Write and read initial context
    db[context_id] = testing_context
    read_context = db[context_id]
    assert testing_context.dict() == read_context.dict()

    # Remove key
    del db[context_id]

    # Add key to misc and request to requests
    read_context.misc.update(new_key="new_value")
    for i in range(1, 5):
        read_context.add_request(Message(text=f"new message: {i}"))
    write_context = read_context.dict()

    # Patch context to use with dict context storage, that doesn't follow read limits
    if not isinstance(db, dict):
        for i in sorted(write_context["requests"].keys())[:2]:
            del write_context["requests"][i]

    # Write and read updated context
    db[context_id] = read_context
    read_context = db[context_id]
    assert write_context == read_context.dict()


def midair_subscript_change_test(db: DBContextStorage, testing_context: Context, context_id: str):
    # Add new requestgs to context
    for i in range(1, 10):
        testing_context.add_request(Message(text=f"new message: {i}"))

    # Make read limit larger (7)
    db[context_id] = testing_context
    db.context_schema.requests.subscript = 7

    # Create a copy of context that simulates expected read value (last 7 requests)
    write_context = testing_context.dict()
    for i in sorted(write_context["requests"].keys())[:-7]:
        del write_context["requests"][i]

    # Check that expected amount of requests was read only
    read_context = db[context_id]
    assert write_context == read_context.dict()

    # Make read limit smaller (2)
    db.context_schema.requests.subscript = 2

    # Create a copy of context that simulates expected read value (last 2 requests)
    write_context = testing_context.dict()
    for i in sorted(write_context["requests"].keys())[:-2]:
        del write_context["requests"][i]

    # Check that expected amount of requests was read only
    read_context = db[context_id]
    assert write_context == read_context.dict()


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
    # Setup schema so that only last request will be written to database
    db.context_schema.requests.subscript = 1

    # Fill database with contexts with one misc value and two requests
    for i in range(1, 101):
        db[f"{context_id}_{i}"] = Context(
            misc={f"key_{i}": f"ctx misc value {i}"},
            requests={0: Message(text="useful message"), i: Message(text="some message")}
        )

    # Setup schema so that all requests will be read from database
    db.context_schema.requests.subscript = ALL_ITEMS

    # Check database length
    assert len(db) == 100

    # Check that both misc and requests are read as expected
    for i in range(1, 101):
        read_ctx = db[f"{context_id}_{i}"]
        assert read_ctx.misc[f"key_{i}"] == f"ctx misc value {i}"
        assert read_ctx.requests[0].text == "useful message"


basic_test.no_dict = False
partial_storage_test.no_dict = False
midair_subscript_change_test.no_dict = True
large_misc_test.no_dict = False
many_ctx_test.no_dict = True
_TEST_FUNCTIONS = [basic_test, partial_storage_test, midair_subscript_change_test, large_misc_test, many_ctx_test]


def run_all_functions(db: DBContextStorage, testing_context: Context, context_id: str):
    frozen_ctx = testing_context.dict()
    for test in _TEST_FUNCTIONS:
        if not (getattr(test, "no_dict", False) and isinstance(db, dict)):
            db.clear()
            test(db, Context.cast(frozen_ctx), context_id)
