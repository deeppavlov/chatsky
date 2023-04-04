from inspect import signature
import ast

import pytest

from dff.utils.parser.dff_project import DFFProject
from dff.utils.parser.base_parser_object import Expression, Call, Python
from dff.utils.parser.namespace import Namespace


def test_referenced_object():
    dff_project = DFFProject.from_dict(
        {
            "main": {
                "proxy_1": "import proxy_1",
                "proxy_2": "import proxy_2",
                "nonexistent": "import mod",
                "other_nonexistent": "from module import object",
                "number": "proxy_1.prox.numbers[proxy_1.numbers.numbers[proxy_2.vars.lower_number]]"
                "[proxy_2.vars.number]",
                "object": "nonexistent._1._2",
                "other_object": "other_nonexistent._3._4",
                "value_nonexistent": "other_nonexistent[proxy_1.prox.numbers[1][2]]",
                "index_nonexistent": "proxy_2.numbers[object]",
                "second_index_nonexistent": "proxy_2.numbers[1][object]",
            },
            "proxy_1": {"prox": "import proxy_2", "numbers": "import other_variables"},
            "proxy_2": {
                "numbers": "from variables import dictionary",
                "vars": "import variables",
            },
            "variables": {
                "dictionary": "{1: {2: 3}}",
                "number": "2",
                "lower_number": "1",
            },
            "other_variables": {"numbers": "{1: 1, 2: 2}"},
        },
        validate=False,
    )

    assert dff_project["main"]["number"] == "3"
    assert dff_project["main"]["proxy_2"] == dff_project["proxy_2"]
    assert dff_project["main"]["nonexistent"] == "mod"
    assert dff_project["main"]["other_nonexistent"] == "module.object"
    assert dff_project["main"]["object"] == "mod._1._2"
    assert dff_project["main"]["other_object"] == "module.object._3._4"
    assert dff_project["main"]["value_nonexistent"] == "module.object[3]"
    assert dff_project["main"]["index_nonexistent"] == "{1: {2: 3,},}[mod._1._2]"
    assert dff_project["main"]["second_index_nonexistent"] == "{2: 3,}[mod._1._2]"


def test_get_args():
    def func(param, another: int = 1, *args, **kwargs):
        ...

    func_call = Expression.from_str("func(1, 2, 3, 4, stuff={'key': 'value'})")
    assert isinstance(func_call, Call)
    args = func_call.get_args(signature(func))
    assert args == {
        "param": Expression.from_obj(1),
        "another": Expression.from_obj(2),
        "args": Expression.from_obj((3, 4)),
        "kwargs": Expression.from_obj({"stuff": {"key": "value"}}),
    }

    func_call = Expression.from_str("func()")
    assert isinstance(func_call, Call)
    with pytest.raises(TypeError) as exc_info:
        _ = func_call.get_args(signature(func))
    assert exc_info.value.args[0] == "missing a required argument: 'param'"

    func_call = Expression.from_str("func(param=2)")
    assert isinstance(func_call, Call)
    args = func_call.get_args(signature(func))
    assert args == {
        "param": Expression.from_obj(2),
        "another": Expression.from_obj(1),
        "args": Expression.from_obj(()),
        "kwargs": Expression.from_obj({}),
    }

    # test alternative naming

    def func(*func_args, **func_kwargs):
        ...

    func_call = Expression.from_str("func(1, 2, 3, 4, stuff={'key': 'value'})")
    assert isinstance(func_call, Call)
    args = func_call.get_args(signature(func))
    assert args == {
        "func_args": Expression.from_obj((1, 2, 3, 4)),
        "func_kwargs": Expression.from_obj({"stuff": {"key": "value"}}),
    }

    # test self / cls omitting

    def func(self):
        ...

    func_call = Expression.from_str("func()")
    assert isinstance(func_call, Call)
    args = func_call.get_args(signature(func))
    assert args == {}

    def func(cls):
        ...

    func_call = Expression.from_str("func()")
    assert isinstance(func_call, Call)
    args = func_call.get_args(signature(func))
    assert args == {}


def test_python_dependencies():
    dff_project = DFFProject.from_dict(
        {
            "main": {
                "transitions": "from .transitions import transitions",
                "variables": "import variables",
                "unrelated_variable": "1",
                "python_object": "len(transitions[1]) > 0 > -2 > (lambda: -5 + variables.number)()",
            },
            "transitions": {
                "number": "from .variables import number",
                "transitions": {
                    "1": "'cnd'",
                    "'two'": "'label'",
                },
            },
            "variables": {
                "number": "7",
                "unrelated_number": "0",
            },
        },
        validate=False,
    )
    python_object = dff_project["main"]["python_object"]
    assert isinstance(python_object, Python)

    assert python_object.dependencies() == {
        "main": {
            "variables",
            "transitions",
            "python_object",
        },
        "transitions": {
            "transitions",
        },
        "variables": {
            "number",
        },
    }


def test_python_dumping():
    file = "\n".join(
        [
            "import obj",
            "import obj2",
            "",
            "",
            "def func():",
            "    ...",
            "",
            "",
            "other_obj = obj",
            "",
            "another_obj = obj",
            "",
            "",
            "async def func():",
            "    ...",
            "",
            "",
            # `Base` is needed because python3.8- and python3.9+ dump parentless class definitions differently
            "class Class(Base):",
            "    ...",
            "",
        ]
    )
    file_dict = {
        "main": {
            "obj": "import obj",
            "obj2": "import obj2",
            "0": "def func():\n    ...",
            "other_obj": "obj",
            "another_obj": "obj",
            "1": "async def func():\n    ...",
            "2": "class Class(Base):\n    ...",
        }
    }

    object_filter = {"main": set(file_dict["main"].keys())}

    # init from ast
    namespace = Namespace.from_ast(ast.parse(file), location=["main"])
    dff_project = DFFProject(namespaces=[namespace], validate=False)

    assert dff_project["main"].dump() == file
    assert dff_project.to_dict(object_filter=object_filter) == file_dict

    # init from dict
    dff_project = DFFProject.from_dict(file_dict, validate=False)

    assert dff_project["main"].dump() == file
    assert dff_project.to_dict(object_filter=object_filter) == file_dict
