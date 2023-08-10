import pytest
from dff.script import Message
from dff.script.slots import RegexpSlot, GroupSlot, FunctionSlot
from dff.script.slots.types import RootSlot, root_slot

# pytest.skip(allow_module_level=True)


@pytest.mark.parametrize(
    ("input", "regexp", "expected", "_set"),
    [
        (Message(text="I am Groot"), "(?<=am ).+", "Groot", True),
        (Message(text="My email is groot@gmail.com"), "(?<=email is ).+", "groot@gmail.com", True),
        (Message(text="I won't tell you my name"), "(?<=name is ).+$", None, False),
    ],
)
def test_regexp(input, regexp, expected, _set, testing_context, testing_pipeline):
    testing_context = testing_context.model_copy()
    testing_context.add_request(input)
    slot = RegexpSlot(name="test", regexp=regexp)
    result = slot.extract_value(testing_context, testing_pipeline)
    assert result == expected
    testing_context.framework_states["slot_storage"][slot.name] = result
    assert slot.is_set()(testing_context, testing_pipeline) == _set


@pytest.mark.parametrize(
    ("input", "children", "expected", "is_set"),
    [
        (
            Message(text="I am Groot. My email is groot@gmail.com"),
            [
                RegexpSlot(name="name", regexp=r"(?<=am ).+?(?=\.)"),
                RegexpSlot(name="email", regexp=r"[a-zA-Z\.]+@[a-zA-Z\.]+"),
            ],
            {"test/name": "Groot", "test/email": "groot@gmail.com"},
            True,
        ),
        (
            Message(text="I am Groot. I won't tell you my name"),
            [
                RegexpSlot(name="name", regexp=r"(?<=am ).+?(?=\.)"),
                RegexpSlot(name="email", regexp=r"[a-zA-Z\.]+@[a-zA-Z\.]+"),
            ],
            {"test/name": "Groot", "test/email": None},
            False,
        ),
    ],
)
def test_group(input, children, expected, is_set, testing_context, testing_pipeline):
    testing_context = testing_context.model_copy()
    testing_context.add_request(input)
    slot = GroupSlot(name="test", children=children)
    assert len(slot.children) == len(children)
    result = slot.extract_value(testing_context, testing_pipeline)
    assert result == expected
    testing_context.framework_states["slot_storage"].update(result)
    assert slot.is_set()(testing_context, testing_pipeline) == is_set


@pytest.mark.parametrize(
    ("input", "func", "expected", "_set"),
    [
        (Message(text="I am Groot"), lambda msg: msg.split(" ")[2], "Groot", True),
        (
            Message(text="My email is groot@gmail.com"),
            lambda msg: [i for i in msg.split(" ") if "@" in i][0],
            "groot@gmail.com",
            True,
        ),
        (
            Message(text="I won't tell you my name"),
            lambda msg: [i for i in msg.split(" ") if "@" in i] or None,
            None,
            False,
        ),
    ],
)
def test_function(input, func, expected, _set, testing_context, testing_pipeline):
    new_testing_context = testing_context.model_copy()
    new_testing_context.add_request(input)
    slot = FunctionSlot(name="test", func=func)
    result = slot.extract_value(new_testing_context, testing_pipeline)
    assert result == expected
    new_testing_context.framework_states["slot_storage"][slot.name] = result
    assert slot.is_set()(new_testing_context, testing_pipeline) == _set


def test_children():
    slot = GroupSlot(name="test", children=[RegexpSlot(name="test", regexp="(?<=am ).+")])
    assert slot.has_children() is True
    slot.children.pop("test")
    assert slot.has_children() is False


@pytest.mark.parametrize(
    ("root_name", "length", "children", "names"),
    [
        (
            "root",
            3,
            [
                RegexpSlot(name="name", regexp=r"(?<=am ).+?(?=\.)"),
                RegexpSlot(name="email", regexp=r"[a-zA-Z\.]+@[a-zA-Z\.]+"),
            ],
            ["root/name", "root/email", "root"],
        ),
        (
            "root",
            4,
            [
                GroupSlot(
                    name="person",
                    children=[
                        RegexpSlot(name="name", regexp=r"(?<=am ).+?(?=\.)"),
                        RegexpSlot(name="email", regexp=r"[a-zA-Z\.]+@[a-zA-Z\.]+"),
                    ],
                )
            ],
            ["root/person/name", "root/person/email", "root/person", "root"],
        ),
        (
            "root",
            7,
            [
                GroupSlot(
                    name="person_1",
                    children=[
                        RegexpSlot(name="name", regexp=r"(?<=am ).+?(?=\.)"),
                        RegexpSlot(name="email", regexp=r"[a-zA-Z\.]+@[a-zA-Z\.]+"),
                    ],
                ),
                GroupSlot(
                    name="person_2",
                    children=[
                        RegexpSlot(name="name", regexp=r"(?<=am ).+?(?=\.)"),
                        RegexpSlot(name="email", regexp=r"[a-zA-Z\.]+@[a-zA-Z\.]+"),
                    ],
                ),
            ],
            None,
        ),
    ],
)
def test_flatten(root_name, length, children, names):
    slot = GroupSlot(name=root_name, children=children)
    flatten_result, _ = root_slot.flatten_slot_tree(slot)
    assert len(flatten_result) == length
    assert all(map(lambda x: x.startswith(root_name), flatten_result.keys()))
    if names:
        assert all(map(lambda x: x in flatten_result, names))


def test_slot_root(root: RootSlot):
    slot = RegexpSlot(name="test", regexp=r".+")
    root.add_slots([slot])
    assert slot.name in root.children
