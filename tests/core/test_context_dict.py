import pytest

from chatsky.context_storages import MemoryContextStorage
from chatsky.context_storages.database import ContextInfo, NameConfig
from chatsky.core.message import Message
from chatsky.core.ctx_dict import ContextDict, MessageContextDict


class TestContextDict:
    @pytest.fixture(scope="function")
    async def empty_dict(self) -> ContextDict:
        # Empty (disconnected) context dictionary
        return MessageContextDict()

    @pytest.fixture(scope="function")
    async def attached_dict(self) -> ContextDict:
        # Attached, but not backed by any data context dictionary
        storage = MemoryContextStorage()
        return await MessageContextDict.new(storage, "ID", NameConfig._requests_field)

    @pytest.fixture(scope="function")
    async def prefilled_dict(self) -> ContextDict:
        # Attached pre-filled context dictionary
        ctx_id = "ctx1"
        storage = MemoryContextStorage(rewrite_existing=True, partial_read_config={"requests": 1})
        main_info = ContextInfo(turn_id=0, created_at=0, updated_at=0)
        requests = [
            (1, Message("longer text", misc={"k": "v"}).model_dump_json().encode()),
            (2, Message("text 2", misc={"1": 0, "2": 8}).model_dump_json().encode()),
        ]
        await storage.update_context(ctx_id, main_info, [(NameConfig._requests_field, requests, list())])
        return await MessageContextDict.connected(storage, ctx_id, NameConfig._requests_field)

    async def test_creation(
        self, empty_dict: ContextDict, attached_dict: ContextDict, prefilled_dict: ContextDict
    ) -> None:
        # Checking creation correctness
        for ctx_dict in [empty_dict, attached_dict, prefilled_dict]:
            assert ctx_dict._storage is not None or ctx_dict == empty_dict
            assert ctx_dict._added == ctx_dict._removed == set()
            if ctx_dict != prefilled_dict:
                assert ctx_dict._items == ctx_dict._hashes == dict()
                assert ctx_dict._keys == set()
            else:
                assert len(ctx_dict._items) == len(ctx_dict._hashes) == 1
                assert ctx_dict._keys == {1, 2}

    async def test_get_set_del(
        self, empty_dict: ContextDict, attached_dict: ContextDict, prefilled_dict: ContextDict
    ) -> None:
        for ctx_dict in [empty_dict, attached_dict, prefilled_dict]:
            # Setting 1 item
            message = Message("message")
            ctx_dict[0] = message
            assert await ctx_dict[0] == message
            assert 0 in ctx_dict._keys
            assert ctx_dict._added == {0}
            assert ctx_dict._items[0] == message
            # Setting several items
            ctx_dict[1] = ctx_dict[2] = ctx_dict[3] = Message()
            messages = (Message("1"), Message("2"), Message("3"))
            ctx_dict[1:] = messages
            assert await ctx_dict[1:] == list(messages)
            assert ctx_dict._keys == {0, 1, 2, 3}
            assert ctx_dict._added == {0, 1, 2, 3}
            # Deleting item
            del ctx_dict[0]
            assert ctx_dict._keys == {1, 2, 3}
            assert ctx_dict._added == {1, 2, 3}
            assert ctx_dict._removed == {0}
            # Getting deleted item
            with pytest.raises(KeyError) as e:
                _ = await ctx_dict[0]
            assert e
            # negative index
            (await ctx_dict[-1]).text = "4"
            assert (await ctx_dict[3]).text == "4"

    async def test_load_len_in_contains_keys_values(self, prefilled_dict: ContextDict) -> None:
        # Checking keys
        assert len(prefilled_dict) == 2
        assert prefilled_dict._keys == {1, 2}
        assert prefilled_dict._added == set()
        assert prefilled_dict.keys() == [1, 2]
        assert 1 in prefilled_dict and 2 in prefilled_dict
        assert set(prefilled_dict._items.keys()) == {2}
        # Loading item
        assert await prefilled_dict.get(100, None) is None
        assert await prefilled_dict.get(1, None) is not None
        assert prefilled_dict._added == set()
        assert len(prefilled_dict._hashes) == 1
        assert len(prefilled_dict._items) == 2
        # Deleting loaded item
        del prefilled_dict[1]
        assert prefilled_dict._removed == {1}
        assert len(prefilled_dict._items) == 1
        assert prefilled_dict._keys == {2}
        assert 1 not in prefilled_dict
        assert set(prefilled_dict.keys()) == {2}
        # Checking remaining item
        assert len(await prefilled_dict.values()) == 1
        assert len(prefilled_dict._items) == 1
        assert prefilled_dict._added == set()

    async def test_other_methods(self, prefilled_dict: ContextDict) -> None:
        # Loading items
        assert len(await prefilled_dict.items()) == 2
        # Poppong first item
        assert await prefilled_dict.pop(1, None) is not None
        assert prefilled_dict._removed == {1}
        assert len(prefilled_dict) == 1
        # Popping nonexistent item
        assert await prefilled_dict.pop(100, None) is None
        # Poppint last item
        assert (await prefilled_dict.popitem())[0] == 2
        assert prefilled_dict._removed == {1, 2}
        # Updating dict with new values
        await prefilled_dict.update({1: Message("some"), 2: Message("random")})
        assert set(prefilled_dict.keys()) == {1, 2}
        # Adding default value to dict
        message = Message("message")
        assert await prefilled_dict.setdefault(3, message) == message
        assert set(prefilled_dict.keys()) == {1, 2, 3}
        # Clearing all the items
        prefilled_dict.clear()
        assert set(prefilled_dict.keys()) == set()

    async def test_eq_validate(self, empty_dict: ContextDict) -> None:
        # Checking empty dict validation
        assert empty_dict == MessageContextDict.model_validate(dict())
        # Checking non-empty dict validation
        empty_dict[0] = Message("msg")
        empty_dict._added = set()
        assert empty_dict == MessageContextDict.model_validate({0: Message("msg")})

    async def test_serialize_store(
        self, empty_dict: ContextDict, attached_dict: ContextDict, prefilled_dict: ContextDict
    ) -> None:
        # Check all the dict types
        for ctx_dict in [empty_dict, attached_dict, prefilled_dict]:
            # Set overwriting existing keys to false
            if ctx_dict._storage is not None:
                ctx_dict._storage.rewrite_existing = False
            # Adding an item
            ctx_dict[0] = Message("message")
            # Loading all pre-filled items
            await ctx_dict.values()
            # Changing one more item (might be pre-filled)
            ctx_dict[2] = Message("another message")
            # Removing the first added item
            del ctx_dict[0]
            # Checking only the changed keys were serialized
            assert set(ctx_dict.model_dump(mode="json").keys()) == {"2"}
        # Throw error if store in disconnected
        if ctx_dict == empty_dict:
            with pytest.raises(KeyError) as e:
                ctx_dict.extract_sync()
            assert e
        else:
            field_name, added_values, deleted_values = ctx_dict.extract_sync()
            assert field_name == NameConfig._requests_field
            assert 2 in [k for k, _ in added_values]
            assert deleted_values == set()
