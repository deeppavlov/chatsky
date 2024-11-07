from chatsky.slots import RegexpSlot, GroupSlot
from chatsky.slots.slots import SlotManager
from chatsky.core import Message

import pytest

test_slot = GroupSlot(
    root_slot=GroupSlot(
        one=RegexpSlot(regexp=r"1"),
        two=RegexpSlot(regexp=r"2"),
        nested_group=GroupSlot(
            three=RegexpSlot(regexp=r"3"),
            four=RegexpSlot(regexp=r"4"),
            allow_partial_extraction=False,
        ),
        nested_partial_group=GroupSlot(
            five=RegexpSlot(regexp=r"5"),
            six=RegexpSlot(regexp=r"6"),
            allow_partial_extraction=True,
        ),
        allow_partial_extraction=True,
    )
)

extracted_slots = {
    "root_slot.one": "1",
    "root_slot.two": "2",
    "root_slot.nested_group.three": "3",
    "root_slot.nested_group.four": "4",
    "root_slot.nested_partial_group.five": "5",
    "root_slot.nested_partial_group.six": "6",
}


@pytest.fixture(scope="function")
def context_with_request(context):
    def inner(request):
        context.add_request(Message(request))
        return context

    return inner


@pytest.fixture(scope="function")
def empty_slot_manager():
    manager = SlotManager()
    manager.set_root_slot(test_slot)
    return manager


def get_extracted_slots(manager: SlotManager):
    values = []
    for slot, value in extracted_slots.items():
        extracted_value = manager.get_extracted_slot(slot)
        if extracted_value.__slot_extracted__:
            if extracted_value.value == value:
                values.append(value)
            else:
                raise RuntimeError(f"Extracted value {extracted_value} does not match expected {value}.")
    return values


@pytest.mark.parametrize(
    "message,extracted",
    [("1 2 3", ["1", "2"]), ("1 3 5", ["1", "5"]), ("3 4 5 6", ["3", "4", "5", "6"])],
)
async def test_partial_extraction(message, extracted, context_with_request, empty_slot_manager):
    await empty_slot_manager.extract_slot("root_slot", context_with_request(message), success_only=False)

    assert extracted == get_extracted_slots(empty_slot_manager)


async def test_slot_storage_update(context_with_request, empty_slot_manager):
    await empty_slot_manager.extract_slot("root_slot", context_with_request("1 3 5"), success_only=False)

    assert get_extracted_slots(empty_slot_manager) == ["1", "5"]

    await empty_slot_manager.extract_slot("root_slot", context_with_request("2 4 6"), success_only=False)

    assert get_extracted_slots(empty_slot_manager) == ["1", "2", "5", "6"]

    await empty_slot_manager.extract_slot("root_slot.nested_group", context_with_request("3 4"), success_only=False)

    assert get_extracted_slots(empty_slot_manager) == ["1", "2", "3", "4", "5", "6"]
