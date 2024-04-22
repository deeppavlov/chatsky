import pytest
from pydantic import ValidationError

from dff.script import (
    GLOBAL,
    Script,
    Node,
    Message,
)


def _create_node(transition, condition, response, pre_response_processing, pre_transitions_processing, misc):
    return Node(
        transitions={transition: condition},
        response=response,
        pre_response_processing=pre_response_processing,
        pre_transitions_processing=pre_transitions_processing,
        misc=misc,
    )


def custom_user_function(ctx, pipeline):
    pass


@pytest.mark.parametrize(
    "transition", [custom_user_function, "node", ("flow", "node"), ("node", 2.5), ("flow", "node", 2)]
)
@pytest.mark.parametrize("condition", [custom_user_function])
@pytest.mark.parametrize("response", [Message("text"), custom_user_function, None])
@pytest.mark.parametrize("pre_response_processing", [{}, {"name": custom_user_function}])
@pytest.mark.parametrize("pre_transitions_processing", [{}, {"name": custom_user_function}])
@pytest.mark.parametrize("misc", [{}, {1: "var"}])
def test_node_initialization(
    transition, condition, response, pre_response_processing, pre_transitions_processing, misc
):
    _create_node(transition, condition, response, pre_response_processing, pre_transitions_processing, misc)


@pytest.mark.parametrize(
    "field,value",
    [
        ("transition", None),
        ("transition", 0),
        ("condition", None),
        ("transition", 0),
        ("response", 0),
        ("pre_response_processing", 0),
        ("pre_transitions_processing", 0),
        ("misc", 0),
    ],
)
def test_node_initialization_raises_validation_error(field, value):
    erroneous_dict = {
        "transition": custom_user_function,
        "condition": custom_user_function,
        "response": custom_user_function,
        "pre_response_processing": custom_user_function,
        "pre_transitions_processing": custom_user_function,
        "misc": {},
        field: value,
    }

    with pytest.raises(ValidationError):
        _create_node(**erroneous_dict)


class TestScript:
    node = Node(misc={"key": "val"})

    script = Script(script={GLOBAL: node})

    def test_global_creation(self):
        assert self.script[GLOBAL][GLOBAL] == self.node

    def test_methods(self):
        assert self.script[GLOBAL] == {GLOBAL: self.node}

        assert self.script.get(GLOBAL) == {GLOBAL: self.node}
        assert self.script.get("", 1) == 1

        assert tuple(self.script.keys()) == (GLOBAL,)

        assert tuple(self.script.values()) == ({GLOBAL: self.node},)

        assert tuple(self.script.items()) == ((GLOBAL, {GLOBAL: self.node}),)

        assert tuple(iter(self.script)) == (GLOBAL,)
