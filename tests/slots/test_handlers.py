import sys

import pytest
import dff.script.logic.slots

from dff.script.logic.slots.handlers import get_values, get_filled_template, extract, unset
from dff.script.logic.slots import FunctionSlot, RootSlot, add_slots
from dff.script.logic.slots.types import BaseSlot
from dff.script.logic.slots.conditions import is_set_any


@pytest.mark.parametrize(
    ["input", "noparams", "expected"],
    [
        ("my name is Groot", False, ["Groot"]),
        ("my name ain't Groot", False, [None]),
        ("my name is Groot", True, ["Groot"]),
        ("my name ain't Groot", True, [None]),
    ],
)
def test_get_template(input, noparams, expected, testing_context, testing_actor, root: RootSlot):
    testing_context.add_request(input)
    slot_name = "creature_name"
    template = "{" + slot_name + "}"
    root.children.clear()
    slot = FunctionSlot(name=slot_name, func=lambda x: x.partition("name is ")[-1] or None)
    add_slots([slot])
    if noparams:
        result_1 = extract(testing_context, testing_actor)
        result_2 = get_values(testing_context, testing_actor)
        result_3 = get_filled_template(template, testing_context, testing_actor)
    else:
        result_1 = extract(testing_context, testing_actor, [slot_name])
        result_2 = get_values(testing_context, testing_actor, [slot_name])
        result_3 = get_filled_template(template, testing_context, testing_actor, [slot_name])
    if result_3 == template:
        result_3 = None
    assert result_1 == result_2 == [result_3] == expected


def test_error(testing_context, testing_actor):
    with pytest.raises(ValueError):
        result = get_filled_template("{non-existent_slot}", testing_context, testing_actor, ["non-existent_slot"])
    assert True


@pytest.mark.parametrize(
    ["slot", "noparams"],
    [
        (dff.script.logic.slots.RegexpSlot(name="test", regexp=".+"), False),
        (dff.script.logic.slots.RegexpSlot(name="test", regexp=".+"), True),
        (
            dff.script.logic.slots.GroupSlot(
                name="test", children=[dff.script.logic.slots.RegexpSlot(name="test", regexp=".+")]
            ),
            False,
        ),
        (
            dff.script.logic.slots.GroupSlot(
                name="test", children=[dff.script.logic.slots.RegexpSlot(name="test", regexp=".+")]
            ),
            True,
        ),
    ],
)
def test_unset(testing_context, testing_actor, slot: BaseSlot, noparams: bool, root: RootSlot):
    root.children.clear()
    add_slots([slot])
    testing_context.add_request("Something")
    if not noparams:
        pre_result = extract(testing_context, testing_actor, [slot.name])
        unset(testing_context, testing_actor, [slot.name])
    else:
        pre_result = extract(testing_context, testing_actor)
        unset(testing_context, testing_actor)
    result = is_set_any([slot.name])(testing_context, testing_actor)
    assert result == False
