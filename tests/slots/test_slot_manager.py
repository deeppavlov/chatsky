import pytest

from chatsky.slots.slots import (
    SlotManager,
    RegexpSlot,
    GroupSlot,
    FunctionSlot,
    ExtractedGroupSlot,
    ExtractedValueSlot,
    SlotNotExtracted,
)
from chatsky.script import Message


def faulty_func(_):
    raise SlotNotExtracted("Error.")


init_value_slot = ExtractedValueSlot.model_construct(
    is_slot_extracted=False,
    extracted_value=SlotNotExtracted("Initial slot extraction."),
    default_value=None,
)


root_slot = GroupSlot(
    person=GroupSlot(
        name=RegexpSlot(regexp=r"(?<=am ).+?(?=\.)"),
        surname=FunctionSlot(func=faulty_func),
        email=RegexpSlot(regexp=r"[a-zA-Z\.]+@[a-zA-Z\.]+"),
    ),
    msg_len=FunctionSlot(func=lambda msg: len(msg.text)),
)


extracted_slot_values = {
    "person.name": ExtractedValueSlot.model_construct(
        is_slot_extracted=True, extracted_value="Bot", default_value=None
    ),
    "person.surname": ExtractedValueSlot.model_construct(
        is_slot_extracted=False, extracted_value=SlotNotExtracted("Error."), default_value=None
    ),
    "person.email": ExtractedValueSlot.model_construct(
        is_slot_extracted=True, extracted_value="bot@bot", default_value=None
    ),
    "msg_len": ExtractedValueSlot.model_construct(is_slot_extracted=True, extracted_value=29, default_value=None),
}


extracted_slot_values["person"] = ExtractedGroupSlot(
    name=extracted_slot_values["person.name"],
    surname=extracted_slot_values["person.surname"],
    email=extracted_slot_values["person.email"],
)


unset_slot = ExtractedValueSlot.model_construct(
    is_slot_extracted=False, extracted_value=SlotNotExtracted("Slot manually unset."), default_value=None
)


init_slot_storage = ExtractedGroupSlot(
    person=ExtractedGroupSlot(
        name=init_value_slot,
        surname=init_value_slot,
        email=init_value_slot,
    ),
    msg_len=init_value_slot,
)


unset_slot_storage = ExtractedGroupSlot(
    person=ExtractedGroupSlot(
        name=unset_slot,
        surname=unset_slot,
        email=unset_slot,
    ),
    msg_len=unset_slot,
)


full_slot_storage = ExtractedGroupSlot(
    person=ExtractedGroupSlot(
        name=extracted_slot_values["person.name"],
        surname=extracted_slot_values["person.surname"],
        email=extracted_slot_values["person.email"],
    ),
    msg_len=extracted_slot_values["msg_len"],
)


class TestSlotManager:
    @pytest.fixture(scope="function")
    def context_with_request(self, context):
        new_ctx = context.model_copy(deep=True)
        new_ctx.add_request(Message(text="I am Bot. My email is bot@bot"))
        return new_ctx

    async def test_init_slot_storage(self):
        assert root_slot.init_value() == init_slot_storage

    @pytest.fixture(scope="function")
    def empty_slot_manager(self):
        manager = SlotManager()
        manager.set_root_slot(root_slot)
        return manager

    @pytest.fixture(scope="function")
    def extracted_slot_manager(self):
        slot_storage = full_slot_storage.model_copy(deep=True)
        return SlotManager(root_slot=root_slot, slot_storage=slot_storage)

    @pytest.fixture(scope="function")
    def fully_extracted_slot_manager(self):
        slot_storage = full_slot_storage.model_copy(deep=True)
        slot_storage.person.surname = ExtractedValueSlot.model_construct(
            extracted_value="Bot", is_slot_extracted=True, default_value=None
        )
        return SlotManager(root_slot=root_slot, slot_storage=slot_storage)

    def test_get_slot_by_name(self, empty_slot_manager):
        assert empty_slot_manager.get_slot("person.name").regexp == r"(?<=am ).+?(?=\.)"
        assert empty_slot_manager.get_slot("person.email").regexp == r"[a-zA-Z\.]+@[a-zA-Z\.]+"
        assert isinstance(empty_slot_manager.get_slot("person"), GroupSlot)
        assert isinstance(empty_slot_manager.get_slot("msg_len"), FunctionSlot)

        with pytest.raises(KeyError):
            empty_slot_manager.get_slot("person.birthday")

        with pytest.raises(KeyError):
            empty_slot_manager.get_slot("intent")

    @pytest.mark.parametrize(
        "slot_name,expected_slot_storage",
        [
            (
                "person.name",
                ExtractedGroupSlot(
                    person=ExtractedGroupSlot(
                        name=extracted_slot_values["person.name"],
                        surname=init_value_slot,
                        email=init_value_slot,
                    ),
                    msg_len=init_value_slot,
                ),
            ),
            (
                "person",
                ExtractedGroupSlot(
                    person=ExtractedGroupSlot(
                        name=extracted_slot_values["person.name"],
                        surname=extracted_slot_values["person.surname"],
                        email=extracted_slot_values["person.email"],
                    ),
                    msg_len=init_value_slot,
                ),
            ),
            (
                "msg_len",
                ExtractedGroupSlot(
                    person=ExtractedGroupSlot(
                        name=init_value_slot,
                        surname=init_value_slot,
                        email=init_value_slot,
                    ),
                    msg_len=extracted_slot_values["msg_len"],
                ),
            ),
        ],
    )
    async def test_slot_extraction(
        self, slot_name, expected_slot_storage, empty_slot_manager, context_with_request, pipeline
    ):
        await empty_slot_manager.extract_slot(slot_name, context_with_request, pipeline)
        assert empty_slot_manager.slot_storage == expected_slot_storage

    async def test_extract_all(self, empty_slot_manager, context_with_request, pipeline):
        await empty_slot_manager.extract_all(context_with_request, pipeline)
        assert empty_slot_manager.slot_storage == full_slot_storage

    @pytest.mark.parametrize(
        "slot_name, expected_slot_storage",
        [
            (
                "person.name",
                ExtractedGroupSlot(
                    person=ExtractedGroupSlot(
                        name=unset_slot,
                        surname=extracted_slot_values["person.surname"],
                        email=extracted_slot_values["person.email"],
                    ),
                    msg_len=extracted_slot_values["msg_len"],
                ),
            ),
            (
                "person",
                ExtractedGroupSlot(
                    person=ExtractedGroupSlot(
                        name=unset_slot,
                        surname=unset_slot,
                        email=unset_slot,
                    ),
                    msg_len=extracted_slot_values["msg_len"],
                ),
            ),
            (
                "msg_len",
                ExtractedGroupSlot(
                    person=ExtractedGroupSlot(
                        name=extracted_slot_values["person.name"],
                        surname=extracted_slot_values["person.surname"],
                        email=extracted_slot_values["person.email"],
                    ),
                    msg_len=unset_slot,
                ),
            ),
        ],
    )
    def test_unset_slot(self, extracted_slot_manager, slot_name, expected_slot_storage):
        extracted_slot_manager.unset_slot(slot_name)
        assert extracted_slot_manager.slot_storage == expected_slot_storage

    def test_unset_all(self, extracted_slot_manager):
        extracted_slot_manager.unset_all_slots()
        assert extracted_slot_manager.slot_storage == unset_slot_storage

    @pytest.mark.parametrize("slot_name", ["person.name", "person", "msg_len"])
    def test_get_extracted_slot(self, extracted_slot_manager, slot_name):
        assert extracted_slot_manager.get_extracted_slot(slot_name) == extracted_slot_values[slot_name]

    def test_get_extracted_slot_raises(self, extracted_slot_manager):
        with pytest.raises(KeyError):
            extracted_slot_manager.get_extracted_slot("none")

    def test_slot_extracted(self, fully_extracted_slot_manager, empty_slot_manager):
        assert fully_extracted_slot_manager.is_slot_extracted("person.name") is True
        assert fully_extracted_slot_manager.is_slot_extracted("person") is True
        with pytest.raises(KeyError):
            fully_extracted_slot_manager.is_slot_extracted("none")
        assert fully_extracted_slot_manager.all_slots_extracted() is True

        assert empty_slot_manager.is_slot_extracted("person.name") is False
        assert empty_slot_manager.is_slot_extracted("person") is False
        with pytest.raises(KeyError):
            empty_slot_manager.is_slot_extracted("none")
        assert empty_slot_manager.all_slots_extracted() is False

    @pytest.mark.parametrize(
        "template,filled_value",
        [
            (
                "Your name is {person.name} {person.surname}, your email: {person.email}.",
                "Your name is Bot None, your email: bot@bot.",
            ),
        ],
    )
    def test_template_filling(self, extracted_slot_manager, template, filled_value):
        assert extracted_slot_manager.fill_template(template) == filled_value

    def test_serializable(self):
        serialized = full_slot_storage.model_dump_json()
        assert full_slot_storage == ExtractedGroupSlot.model_validate_json(serialized)
