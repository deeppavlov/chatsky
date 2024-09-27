from typing import Any, Optional

from pydantic import TypeAdapter

from chatsky.context_storages import DBContextStorage
from chatsky.context_storages.database import FieldConfig
from chatsky import Pipeline, Context, Message
from chatsky.core.context import FrameworkData
from chatsky.utils.context_dict.ctx_dict import ContextDict
from chatsky.utils.testing import TOY_SCRIPT_KWARGS, HAPPY_PATH, check_happy_path


def _setup_context_storage(
        db: DBContextStorage,
        rewrite_existing: Optional[bool] = None,
        labels_config: Optional[FieldConfig] = None,
        requests_config: Optional[FieldConfig] = None,
        responses_config: Optional[FieldConfig] = None,
        misc_config: Optional[FieldConfig] = None,
        all_config: Optional[FieldConfig] = None,
    ) -> None:
    if rewrite_existing is not None:
        db.rewrite_existing = rewrite_existing
    if all_config is not None:
        labels_config = requests_config = responses_config = misc_config = all_config
    if labels_config is not None:
        db.labels_config = labels_config
    if requests_config is not None:
        db.requests_config = requests_config
    if responses_config is not None:
        db.responses_config = responses_config
    if misc_config is not None:
        db.misc_config = misc_config


def _attach_ctx_to_db(context: Context, db: DBContextStorage) -> None:
    context._storage = db
    context.labels._storage = db
    context.labels._field_name = db.labels_config.name
    context.labels._key_type = TypeAdapter(int)
    context.labels._value_type = TypeAdapter(Message)
    context.requests._storage = db
    context.requests._field_name = db.requests_config.name
    context.requests._key_type = TypeAdapter(int)
    context.requests._value_type = TypeAdapter(Message)
    context.responses._storage = db
    context.responses._field_name = db.responses_config.name
    context.responses._key_type = TypeAdapter(int)
    context.responses._value_type = TypeAdapter(Message)
    context.misc._storage = db
    context.misc._field_name = db.misc_config.name
    context.misc._key_type = TypeAdapter(str)
    context.misc._value_type = TypeAdapter(Any)


async def basic_test(db: DBContextStorage, testing_context: Context) -> None:
    _attach_ctx_to_db(testing_context, db)
    # Test nothing exists in database
    nothing = await db.load_main_info(testing_context.id)
    assert nothing is None

    # Test context main info can be stored and loaded
    await db.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at, testing_context._updated_at, testing_context.framework_data.model_dump_json().encode())
    turn_id, created_at, updated_at, framework_data = await db.load_main_info(testing_context.id)
    assert testing_context.current_turn_id == turn_id
    assert testing_context._created_at == created_at
    assert testing_context._updated_at == updated_at
    assert testing_context.framework_data == FrameworkData.model_validate_json(framework_data)

    # Test context main info can be updated
    testing_context.framework_data.stats["key"] = "value"
    await db.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at, testing_context._updated_at, testing_context.framework_data.model_dump_json().encode())
    turn_id, created_at, updated_at, framework_data = await db.load_main_info(testing_context.id)
    assert testing_context.framework_data == FrameworkData.model_validate_json(framework_data)

    # Test context fields can be stored and loaded
    requests_dump = [(k, v.model_dump_json().encode()) for k, v in await testing_context.requests.items()]
    await db.update_field_items(testing_context.id, db.requests_config.name, requests_dump)
    requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
    assert testing_context.requests == {k: Message.model_validate_json(v) for k, v in requests}

    # Test context fields keys can be loaded
    req_keys = await db.load_field_keys(testing_context.id, db.requests_config.name)
    assert testing_context.requests.keys() == list(req_keys)

    # Test context values can be loaded
    req_vals = await db.load_field_items(testing_context.id, db.requests_config.name, set(req_keys))
    assert await testing_context.requests.values() == [Message.model_validate_json(val) for val in req_vals]

    # Add some sample requests to the testing context and make their binary dump
    await testing_context.requests.update({0: Message("new message text"), 1: Message("other message text")})
    requests_dump = [(k, v.model_dump_json().encode()) for k, v in await testing_context.requests.items()]

    # Test context values can be updated
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
    await db.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at, testing_context._updated_at, testing_context.framework_data.model_dump_json().encode())
    await db.update_field_items(testing_context.id, db.requests_config.name, requests_dump)
    await db.clear_all()
    nothing = await db.load_main_info(testing_context.id)
    requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
    req_keys = await db.load_field_keys(testing_context.id, db.requests_config.name)
    req_vals = await db.load_field_items(testing_context.id, db.requests_config.name, set(req_keys))
    assert nothing is None
    assert dict() == dict(requests)
    assert set() == set(req_keys)
    assert list() == [Message.model_validate_json(val) for val in req_vals]


async def partial_storage_test(db: DBContextStorage, testing_context: Context) -> None:
    _attach_ctx_to_db(testing_context, db)
    # Store some data in storage
    requests_dump = [(k, v.model_dump_json().encode()) for k, v in await testing_context.requests.items()]
    await db.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at, testing_context._updated_at, testing_context.framework_data.model_dump_json().encode())
    await db.update_field_items(testing_context.id, db.requests_config.name, requests_dump)

    # Test getting keys with 0 subscription
    _setup_context_storage(db, requests_config=FieldConfig(name=db.requests_config.name, subscript="__none__"))
    requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
    assert 0 == len(requests)

    # Test getting keys with standard (3) subscription
    _setup_context_storage(db, requests_config=FieldConfig(name=db.requests_config.name, subscript=3))
    requests = await db.load_field_latest(testing_context.id, db.requests_config.name)
    assert len(testing_context.requests.keys()) == len(requests)


async def large_misc_test(db: DBContextStorage, testing_context: Context) -> None:
    _attach_ctx_to_db(testing_context, db)
    BIG_NUMBER = 10

    # Store data main info in storage
    await db.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at, testing_context._updated_at, testing_context.framework_data.model_dump_json().encode())

    # Fill context misc with data and store it in database
    testing_context.misc = ContextDict.model_validate({f"key_{i}": f"data number #{i}".encode() for i in range(BIG_NUMBER)})
    await db.update_field_items(testing_context.id, db.misc_config.name, await testing_context.misc.items())

    # Check data keys stored in context
    misc = await db.load_field_keys(testing_context.id, db.misc_config.name)
    assert len(testing_context.misc.keys()) == len(misc)

    # Check data values stored in context
    misc_keys = await db.load_field_keys(testing_context.id, db.misc_config.name)
    misc_vals = await db.load_field_items(testing_context.id, db.misc_config.name, set(misc_keys))
    for k, v in zip(misc_keys, misc_vals):
        assert await testing_context.misc[k] == v


async def many_ctx_test(db: DBContextStorage, _: Context) -> None:
    # Fill database with contexts with one misc value and two requests
    for i in range(1, 101):
        ctx = await Context.connected(db, ("flow", "node"), f"ctx_id_{i}")
        await ctx.misc.update({f"key_{i}": f"ctx misc value {i}"})
        ctx.requests[0] = Message("useful message")
        ctx.requests[i] = Message("some message")
        await ctx.store()

    # Check that both misc and requests are read as expected
    for i in range(1, 101):
        ctx = await Context.connected(db, ("flow", "node"), f"ctx_id_{i}")
        assert await ctx.misc[f"key_{i}"] == f"ctx misc value {i}"
        assert (await ctx.requests[0]).text == "useful message"
        assert (await ctx.requests[i]).text == "some message"


async def integration_test(db: DBContextStorage, testing_context: Context) -> None:
    # Attach context to context storage to perform operations on context level
    _attach_ctx_to_db(testing_context, db)

    # Setup context storage for automatic element loading
    _setup_context_storage(
        db,
        rewrite_existing=True,
        labels_config=FieldConfig(name=db.labels_config.name, subscript="__all__"),
        requests_config=FieldConfig(name=db.requests_config.name, subscript="__all__"),
        responses_config=FieldConfig(name=db.responses_config.name, subscript="__all__"),
        misc_config=FieldConfig(name=db.misc_config.name, subscript="__all__"),
    )

    # Store context main data first
    byted_framework_data = testing_context.framework_data.model_dump_json().encode()
    await testing_context._storage.update_main_info(testing_context.id, testing_context.current_turn_id, testing_context._created_at, testing_context._updated_at, byted_framework_data)

    # Check labels storing, deleting and retrieveing
    await testing_context.labels.store()
    labels = await ContextDict.connected(db, testing_context.id, db.labels_config.name, Message)
    await db.delete_field_keys(testing_context.id, db.labels_config.name, [str(k) for k in testing_context.labels.keys()])
    assert testing_context.labels == labels

    # Check requests storing, deleting and retrieveing
    await testing_context.requests.store()
    requests = await ContextDict.connected(db, testing_context.id, db.requests_config.name, Message)
    await db.delete_field_keys(testing_context.id, db.requests_config.name, [str(k) for k in testing_context.requests.keys()])
    assert testing_context.requests == requests

    # Check responses storing, deleting and retrieveing
    await testing_context.responses.store()
    responses = await ContextDict.connected(db, testing_context.id, db.responses_config.name, Message)
    await db.delete_field_keys(testing_context.id, db.responses_config.name, [str(k) for k in testing_context.responses.keys()])
    assert testing_context.responses == responses

    # Check misc storing, deleting and retrieveing
    await testing_context.misc.store()
    misc = await ContextDict.connected(db, testing_context.id, db.misc_config.name, Any)
    await db.delete_field_keys(testing_context.id, db.misc_config.name, [f'"{k}"' for k in testing_context.misc.keys()])
    assert testing_context.misc == misc

    # Check whole context storing, deleting and retrieveing
    await testing_context.store()
    context = await Context.connected(db, None, testing_context.id)
    await db.delete_main_info(testing_context.id)
    assert testing_context == context


async def pipeline_test(db: DBContextStorage, _: Context) -> None:
    # Test Pipeline workload on DB
    pipeline = Pipeline(**TOY_SCRIPT_KWARGS, context_storage=db)
    check_happy_path(pipeline, happy_path=HAPPY_PATH)


_TEST_FUNCTIONS = [
    basic_test,
    partial_storage_test,
    large_misc_test,
    many_ctx_test,
    integration_test,
    pipeline_test,
]


async def run_all_functions(db: DBContextStorage, testing_context: Context):
    frozen_ctx = testing_context.model_dump_json()
    for test in _TEST_FUNCTIONS:
        ctx = Context.model_validate_json(frozen_ctx)
        await db.clear_all()
        await test(db, ctx)
