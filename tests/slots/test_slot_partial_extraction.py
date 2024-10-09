from chatsky import (
    RESPONSE,
    TRANSITIONS,
    PRE_TRANSITION,
    PRE_RESPONSE,
    GLOBAL,
    LOCAL,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    processing as proc,
    responses as rsp,
)

from chatsky.slots import RegexpSlot, GroupSlot
from chatsky.slots.slots import SlotManager, ExtractedValueSlot, ExtractedGroupSlot
from chatsky.core import Message, Context

from chatsky.utils.testing import (
    check_happy_path,
)

import pytest

test_slot = GroupSlot(
        person=GroupSlot(
            username=RegexpSlot(
            regexp=r"([a-z]+_[a-z]+)",
            match_group_idx=1,
        ),
            email=RegexpSlot(
            regexp=r"([a-z]+@[a-z]+\.[a-z]+)",
            match_group_idx=1,
        ),
            allow_partially_extracted=True
        )
    )


extracted_slot_values_turn_1 = {
    "person.username": ExtractedValueSlot.model_construct(
        is_slot_extracted=True, extracted_value="test_name", default_value=None
    ),
    "person.email": ExtractedValueSlot.model_construct(
        is_slot_extracted=True, extracted_value="test@email.com", default_value=None
    ),
}

extracted_slot_values_turn_2 = {
    "person.username": ExtractedValueSlot.model_construct(
        is_slot_extracted=True, extracted_value="new_name", default_value=None
    ),
    "person.email": ExtractedValueSlot.model_construct(
        is_slot_extracted=True, extracted_value="test@email.com", default_value=None
    ),
}

@pytest.fixture(scope="function")
def context_with_request_1(context):
    new_ctx = context.model_copy(deep=True)
    new_ctx.add_request(Message(text="I am test_name. My email is test@email.com"))
    return new_ctx

@pytest.fixture(scope="function")
def context_with_request_2(context):
    context.add_request(Message(text="I am new_name."))
    return context

@pytest.fixture(scope="function")
def empty_slot_manager():
    manager = SlotManager()
    manager.set_root_slot(test_slot)
    return manager

@pytest.mark.parametrize(
    "slot_name,expected_slot_storage_1,expected_slot_storage_2",
    [
        (
            "person",
            ExtractedGroupSlot(
                person=ExtractedGroupSlot(
                    username=extracted_slot_values_turn_1["person.username"],
                    email=extracted_slot_values_turn_1["person.email"],
                )
            ),
            ExtractedGroupSlot(
                person=ExtractedGroupSlot(
                    username=extracted_slot_values_turn_2["person.username"],
                    email=extracted_slot_values_turn_2["person.email"],
                )
            ),
        ),
    ],
)
async def test_slot_extraction(slot_name, expected_slot_storage_1, expected_slot_storage_2, empty_slot_manager, context_with_request_1, context_with_request_2):
    await empty_slot_manager.extract_slot(slot_name, context_with_request_1, success_only=False)
    assert empty_slot_manager.slot_storage == expected_slot_storage_1
    await empty_slot_manager.extract_slot(slot_name, context_with_request_2, success_only=False)
    assert empty_slot_manager.slot_storage == expected_slot_storage_2