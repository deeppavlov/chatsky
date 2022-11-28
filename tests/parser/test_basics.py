import ast

from dff.script.parser.base_parser_object import Dict, Expression, Python, String


def test_just_works():
    obj = Expression.from_ast(ast.parse("{1: {2: '3'}}").body[0].value)
    assert isinstance(obj, Dict)
    assert str(obj.children["Python(1)"]["value"]) == "{2: '3'}"


def test_path():
    obj = Expression.from_ast(ast.parse("{1: {2: '3'}}").body[0].value)
    assert obj.children["Python(1)"]["value"].children["Python(2)"]["key"] == \
           obj.resolve_path(["Python(1)", "value", "Python(2)", "key"])


def test_multiple_keys():
    obj = Expression.from_ast(ast.parse("{1: 1, '1': '1'}").body[0].value)
    assert repr(obj.resolve_path(["Python(1)", "value"])) == "Python(1)"
    assert repr(obj.resolve_path(["Python(1)", "key"])) == "Python(1)"
    assert repr(obj.resolve_path(["String(1)", "value"])) == "String(1)"
    assert repr(obj.resolve_path(["String(1)", "key"])) == "String(1)"


def test_get_item():
    obj = Expression.from_ast(ast.parse("{1: 1, '1': '1'}").body[0].value)
    assert isinstance(obj, Dict)
    assert obj[Python("1")] == Python("1")
    assert obj["Python(1)"] == Python("1")
    assert obj[String("1")] == String("1")
    assert obj["String(1)"] == String("1")
