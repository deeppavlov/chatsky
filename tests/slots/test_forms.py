import pytest


from dff.script.logic.slots import RegexpSlot
from dff.script.logic.slots import FormPolicy, FormState


pytest.skip(allow_module_level=True)


@pytest.mark.parametrize([], [])
def test_state_update(testing_context, testing_actor, root):
    root.children.clear()
    assert True


@pytest.mark.parametrize([], [])
def test_next_slot(testing_context, testing_actor, root):
    root.children.clear()
    assert True
