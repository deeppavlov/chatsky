import pytest

from chatsky.context_storages import MemoryContextStorage
from chatsky.context_storages.database import FieldConfig
from chatsky.script.core.context import FrameworkData
from chatsky.script.core.message import Message
from chatsky.utils.context_dict import ContextDict


class TestContextDict:
    @pytest.fixture(scope="function")
    async def empty_dict(self) -> ContextDict:
        # Empty (disconnected) context dictionary
        return ContextDict()

    @pytest.fixture(scope="function")
    async def attached_dict(self) -> ContextDict:
        # Attached, but not backed by any data context dictionary
        storage = MemoryContextStorage()
        return await ContextDict.new(storage, "ID", "requests")

    @pytest.fixture(scope="function")
    async def prefilled_dict(self) -> ContextDict:
        # Attached pre-filled context dictionary
        config = {"requests": FieldConfig(name="requests", subscript="__none__")}
        storage = MemoryContextStorage(rewrite_existing=True, configuration=config)
        await storage.update_main_info("ctx1", 0, 0, FrameworkData().model_dump_json())
        requests = [(1, Message("longer text", misc={"k": "v"}).model_dump_json()), (2, Message("text 2", misc={"1": 0, "2": 8}).model_dump_json())]
        await storage.update_field_items("ctx1", "requests", requests)
        return await ContextDict.connected(storage, "ctx1", "requests", Message)

    @pytest.mark.asyncio
    async def test_creation(self, empty_dict: ContextDict, attached_dict: ContextDict, prefilled_dict: ContextDict) -> None:
        # Checking creation correctness
        for ctx_dict in [empty_dict, attached_dict, prefilled_dict]:
            assert ctx_dict._storage is not None or ctx_dict == empty_dict
            assert ctx_dict._items == ctx_dict._hashes == dict()
            assert ctx_dict._added == ctx_dict._removed == set()
            assert ctx_dict._keys == set() if ctx_dict != prefilled_dict else {1, 2}

    @pytest.mark.asyncio
    async def test_get_set_del(self, empty_dict: ContextDict, attached_dict: ContextDict, prefilled_dict: ContextDict) -> None:
        for ctx_dict in [empty_dict, attached_dict, prefilled_dict]:
            # Setting 1 item
            message = Message("message")
            ctx_dict[0] = message
            assert await ctx_dict[0] == message
            assert 0 in ctx_dict._keys
            assert ctx_dict._added == {0}
            assert ctx_dict._items == {0: message}
            # Setting several items
            ctx_dict[1] = ctx_dict[2] = ctx_dict[3] = None
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

    @pytest.mark.asyncio
    async def test_load_len_in_contains_keys_values(self, prefilled_dict: ContextDict) -> None:
        # Checking keys
        assert len(prefilled_dict) == 2
        assert prefilled_dict._keys == {1, 2}
        assert prefilled_dict._added == set()
        assert prefilled_dict.keys() == {1, 2}
        assert 1 in prefilled_dict and 2 in prefilled_dict
        assert prefilled_dict._items == dict()
        # Loading item
        assert await prefilled_dict.get(100, None) is None
        assert await prefilled_dict.get(1, None) is not None
        assert prefilled_dict._added == set()
        assert len(prefilled_dict._hashes) == 1
        assert len(prefilled_dict._items) == 1
        # Deleting loaded item
        del prefilled_dict[1]
        assert prefilled_dict._removed == {1}
        assert len(prefilled_dict._items) == 0
        assert prefilled_dict._keys == {2}
        assert 1 not in prefilled_dict
        assert prefilled_dict.keys() == {2}
        # Checking remaining item
        assert len(await prefilled_dict.values()) == 1
        assert len(prefilled_dict._items) == 1
        assert prefilled_dict._added == set()

    @pytest.mark.asyncio
    async def test_other_methods(self, prefilled_dict: ContextDict) -> None:
        # Loading items
        assert len(await prefilled_dict.items()) == 2
        # Poppong first item
        assert await prefilled_dict.pop(1, None) is not None
        assert prefilled_dict._removed == {1}
        assert len(prefilled_dict) == 1
        # Popping nonexistent item
        assert await prefilled_dict.pop(100, None) == None
        # Poppint last item
        assert (await prefilled_dict.popitem())[0] == 2
        assert prefilled_dict._removed == {1, 2}
        # Updating dict with new values
        await prefilled_dict.update({1: Message("some"), 2: Message("random")})
        assert prefilled_dict.keys() == {1, 2}
        # Adding default value to dict
        message = Message("message")
        assert await prefilled_dict.setdefault(3, message) == message
        assert prefilled_dict.keys() == {1, 2, 3}
        # Clearing all the items
        prefilled_dict.clear()
        assert prefilled_dict.keys() == set()

    @pytest.mark.asyncio
    async def test_eq_validate(self, empty_dict: ContextDict) -> None:
        # Checking empty dict validation
        assert empty_dict == ContextDict.model_validate(dict())
        # Checking non-empty dict validation
        empty_dict[0] = Message("msg")
        empty_dict._added = set()
        assert empty_dict == ContextDict.model_validate({0: Message("msg")})

    @pytest.mark.asyncio
    async def test_serialize_store(self, empty_dict: ContextDict, attached_dict: ContextDict, prefilled_dict: ContextDict) -> None:
        for ctx_dict in [empty_dict, attached_dict, prefilled_dict]:
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
                await ctx_dict.store()
            assert e
        else:
            await ctx_dict.store()
