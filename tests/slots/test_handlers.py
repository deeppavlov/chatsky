import pytest
from dff.script import slots, Message

from dff.script.slots.handlers import get_values, get_filled_template, extract, unset
from dff.script.slots import FunctionSlot
from dff.script.slots.types import BaseSlot
from dff.pipeline.conditions import all_condition, any_condition
from dff.script.slots.conditions import slot_extracted_condition


@pytest.mark.parametrize(
    ["input", "noparams", "expected"],
    [
        (Message(text="my name is Groot"), False, ["Groot"]),
        (Message(text="my name ain't Groot"), False, [None]),
        (Message(text="my name is Groot"), True, ["Groot"]),
        (Message(text="my name ain't Groot"), True, [None]),
    ],
)
def test_get_template(input, noparams, expected, testing_context, testing_pipeline, root):
    testing_context.add_request(input)
    slot_name = "creature_name"
    template = "{" + slot_name + "}"
    root.children.clear()
    slot = FunctionSlot(name=slot_name, func=lambda x: x.partition("name is ")[-1] or None)
    if noparams:
        result_1 = extract(testing_context, testing_pipeline)
        result_2 = get_values(testing_context, testing_pipeline)
        result_3 = get_filled_template(template, testing_context, testing_pipeline)
    else:
        result_1 = extract(testing_context, testing_pipeline, [slot.name])
        result_2 = get_values(testing_context, testing_pipeline, [slot.name])
        result_3 = get_filled_template(template, testing_context, testing_pipeline, [slot.name])
    if result_3 == template:
        result_3 = None
    assert result_1 == result_2 == [result_3] == expected


def test_error(testing_context, testing_pipeline):
    with pytest.raises(ValueError):
        _ = get_filled_template("{non-existent_slot}", testing_context, testing_pipeline, ["non-existent_slot"])
    assert True


@pytest.mark.parametrize(
    ["slot", "noparams"],
    [
        (slots.RegexpSlot(name="test", regexp=".+"), False),
        (slots.RegexpSlot(name="test", regexp=".+"), True),
        (
            slots.GroupSlot(name="test", children=[slots.RegexpSlot(name="test", regexp=".+")]),
            False,
        ),
        (
            slots.GroupSlot(name="test", children=[slots.RegexpSlot(name="test", regexp=".+")]),
            True,
        ),
    ],
)
def test_unset(testing_context, testing_pipeline, slot: BaseSlot, noparams: bool, root):
    root.children.clear()
    root.add_slots([slot])
    testing_context.add_request(Message(text="Something"))
    if not noparams:
        _ = extract(testing_context, testing_pipeline, [slot.name])
        unset(testing_context, testing_pipeline, [slot.name])
    else:
        _ = extract(testing_context, testing_pipeline)
        unset(testing_context, testing_pipeline)
    result = any_condition(slot_extracted_condition(slot.name))(testing_context, testing_pipeline)
    _ = all_condition(slot_extracted_condition(slot.name))(testing_context, testing_pipeline)
    assert result is False
