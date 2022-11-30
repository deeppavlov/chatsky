import ast

from dff.script.parser.base_parser_object import Dict, Expression, Python, String, Import
from dff.script.parser.namespace import Namespace
from dff.script.parser.dff_project import DFFProject


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


def test_import_resolution():
    namespace1 = Namespace.from_ast(ast.parse("import namespace2"), location=["namespace1"])
    namespace2 = Namespace.from_ast(ast.parse("import namespace1"), location=["namespace2"])
    dff_project = DFFProject([namespace1, namespace2])
    import_stmt = dff_project.resolve_path(["namespace1", "namespace2"])

    assert isinstance(import_stmt, Import)
    assert import_stmt.resolve_self == namespace2
    assert import_stmt == namespace1.resolve_path(["namespace2"])
    assert import_stmt.path == ["namespace1", "namespace2"]


def test_multiple_imports():
    namespace1 = Namespace.from_ast(ast.parse("import namespace2, namespace3"), location=["namespace1"])
    namespace2 = Namespace.from_ast(ast.parse(""), location=["namespace2"])
    namespace3 = Namespace.from_ast(ast.parse(""), location=["namespace3"])
    dff_project = DFFProject([namespace1, namespace2, namespace3])

    import_2 = dff_project.resolve_path(["namespace1", "namespace2"])
    import_3 = dff_project.resolve_path(["namespace1", "namespace3"])

    assert isinstance(import_2, Import)
    assert isinstance(import_3, Import)

    assert import_2.resolve_self == namespace2
    assert import_3.resolve_self == namespace3

    assert str(import_2) == "import namespace2"
    assert str(import_3) == "import namespace3"


def test_multilevel_import_resolution():
    namespace1 = Namespace.from_ast(ast.parse("import module.namespace2 as n2"), location=["namespace1"])
    namespace2 = Namespace.from_ast(ast.parse("import namespace1"), location=["module", "namespace2"])
    dff_project = DFFProject([namespace1, namespace2])
    import_stmt1 = dff_project.resolve_path(["namespace1", "n2"])

    assert isinstance(import_stmt1, Import)
    assert import_stmt1.resolve_self == namespace2
    assert import_stmt1 == namespace1.resolve_path(["n2"])
    assert import_stmt1.path == ["namespace1", "n2"]


def test_assignment():
    namespace = Namespace.from_ast(ast.parse("a = 1"), location=["namespace"])

    assert namespace["a"] == Python("1")
    assert namespace.resolve_path(["a", "value"]) == Python("1")


def test_import_from():
    namespace1 = Namespace.from_ast(ast.parse("import module.namespace2 as n2"), location=["namespace1"])
    namespace2 = Namespace.from_ast(ast.parse("from . import a"), location=["module", "namespace2"])
    namespace3 = Namespace.from_ast(ast.parse("a = 1"), location=["module", "__init__"])
    dff_project = DFFProject([namespace1, namespace2, namespace3])

    assert dff_project["namespace1"]["n2"].resolve_self["a"] == Python("1")
    assert namespace2["a"] == Python("1")

def test_name():
    namespace1 = Namespace.from_ast(ast.parse("a=b=1\nc=a\nd=b"), location=["namespace1"])

    assert namespace1["c"].absolute == Python("1")
    assert namespace1["d"].absolute == Python("1")
