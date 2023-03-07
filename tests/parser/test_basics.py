import ast
from sys import version_info

from dff.utils.parser.base_parser_object import Dict, Expression, Python, Import, Attribute, Subscript, Call
from dff.utils.parser.namespace import Namespace
from dff.utils.parser.dff_project import DFFProject


def test_just_works():
    obj = Expression.from_str("{1: {2: '3'}}")
    assert isinstance(obj, Dict)
    assert str(obj.children["value_1"]) == """{
    2: '3',
}"""


def test_path():
    obj = Expression.from_str("{1: {2: '3'}}")
    assert obj.children["value_1"].children["key_2"] == \
           obj.resolve_path(("value_1", "key_2"))


def test_multiple_keys():
    obj = Expression.from_str("{1: 1, '1': '1'}")
    assert obj.resolve_path(("value_1",)) == "1"
    assert obj.resolve_path(("key_1",)) == "1"
    assert obj.resolve_path(("value_'1'",)) == "'1'"
    assert obj.resolve_path(("key_'1'",)) == "'1'"


def test_get_item():
    obj = Expression.from_str("{1: 1, '1': '1'}")
    assert isinstance(obj, Dict)
    assert obj["1"] == "1"
    assert obj["'1'"] == "'1'"


def test_import_resolution():
    namespace1 = Namespace.from_ast(ast.parse("import namespace2"), location=["namespace1"])
    namespace2 = Namespace.from_ast(ast.parse("import namespace1"), location=["namespace2"])
    dff_project = DFFProject([namespace1, namespace2], validate=False)
    import_stmt = dff_project.resolve_path(("namespace1", "namespace2"))

    assert isinstance(import_stmt, Import)
    assert import_stmt._resolve_once == namespace2
    assert import_stmt == namespace1.resolve_path(("namespace2",))
    assert import_stmt.path == ("namespace1", "namespace2")


def test_multiple_imports():
    namespace1 = Namespace.from_ast(ast.parse("import namespace2, namespace3"), location=["namespace1"])
    namespace2 = Namespace.from_ast(ast.parse(""), location=["namespace2"])
    namespace3 = Namespace.from_ast(ast.parse(""), location=["namespace3"])
    dff_project = DFFProject([namespace1, namespace2, namespace3], validate=False)

    import_2 = dff_project.resolve_path(("namespace1", "namespace2"))
    import_3 = dff_project.resolve_path(("namespace1", "namespace3"))

    assert isinstance(import_2, Import)
    assert isinstance(import_3, Import)

    assert import_2._resolve_once == namespace2
    assert import_3._resolve_once == namespace3

    assert str(import_2) == "import namespace2"
    assert str(import_3) == "import namespace3"


def test_multilevel_import_resolution():
    namespace1 = Namespace.from_ast(ast.parse("import module.namespace2 as n2"), location=["namespace1"])
    namespace2 = Namespace.from_ast(ast.parse("import namespace1"), location=["module", "namespace2"])
    dff_project = DFFProject([namespace1, namespace2], validate=False)
    import_stmt1 = dff_project.resolve_path(("namespace1", "n2"))

    assert isinstance(import_stmt1, Import)
    assert import_stmt1._resolve_once == namespace2
    assert import_stmt1 == namespace1.resolve_path(("n2",))
    assert import_stmt1.path == ("namespace1", "n2")


def test_assignment():
    namespace = Namespace.from_ast(ast.parse("a = 1"), location=["namespace"])

    assert namespace["a"] == Python.from_str("1")
    assert namespace.resolve_path(("a", "value")) == Python.from_str("1")


def test_import_from():
    namespace1 = Namespace.from_ast(ast.parse("import module.namespace2 as n2"), location=["namespace1"])
    namespace2 = Namespace.from_ast(ast.parse("from . import a"), location=["module", "namespace2"])
    namespace3 = Namespace.from_ast(ast.parse("a = 1"), location=["module", "__init__"])
    dff_project = DFFProject([namespace1, namespace2, namespace3], validate=False)

    assert namespace2["a"] == Python.from_str("1")
    assert Python.from_str("1") == namespace2["a"]
    assert dff_project["namespace1"]["n2"].absolute["a"] == Python.from_str("1")


def test_name():
    namespace1 = Namespace.from_ast(ast.parse("a=b=1\nc=a\nd=b"), location=["namespace1"])

    assert namespace1["c"] == Python.from_str("1")
    assert namespace1["d"] == Python.from_str("1")


def test_attribute():
    namespace1 = Namespace.from_ast(ast.parse("import namespace2 as n2\na=n2.a"), location=["namespace1"])
    namespace2 = Namespace.from_ast(ast.parse("a=1"), location=["namespace2"])
    dff_project = DFFProject([namespace1, namespace2], validate=False)

    assert isinstance(namespace1["a"], Attribute)
    assert namespace1["a"] == namespace2["a"] == Python.from_str("1")


def test_subscript():
    namespace = Namespace.from_ast(ast.parse("a = {1: {2: 3}}\nb = a[1][2]"), location=["namespace"])

    assert isinstance(namespace["b"], Subscript)
    assert namespace["b"] == Python.from_str("3")


def test_iterable():
    namespace = Namespace.from_ast(ast.parse("a = [1, 2, 3]\nb = a[2]"), location=["namespace"])

    assert namespace["b"] == "3"
    assert namespace["a"]["0"] == "1"

    for index, element in enumerate(namespace["a"]):
        assert element == str(index + 1)

    assert len(namespace["a"]) == 3


def test_call():
    namespace = Namespace.from_ast(ast.parse("import Actor\na = Actor(1, 2, c=3)"), location=["namespace"])
    dff_project = DFFProject([namespace], validate=False)

    call = namespace["a"]

    assert isinstance(call, Call)
    assert repr(call.resolve_path(("func",))) == "Name(Actor)"
    assert call.resolve_path(("arg_1",)) == Python.from_str("2")
    assert call.resolve_path(("keyword_c",)) == Python.from_str("3")
    assert call.func_name == "Actor"

    namespace = Namespace.from_ast(ast.parse("a = (lambda x, y, z: 1)(1, 2, c=3)"), location=["namespace"])
    dff_project = DFFProject([namespace], validate=False)

    call = namespace["a"]
    assert isinstance(call, Call)
    if version_info >= (3, 9):
        assert call.func_name == "lambda x, y, z: 1"
    else:
        assert call.func_name == "(lambda x, y, z: 1)"


def test_comprehensions():
    list_comp_str = "[x for x in a]"
    set_comp_str = "{x for q in b for x in q}"
    dict_comp_str = "{x: x ** 2 for q in c if q for x in q if x > 0}"
    gen_comp_str = "((x, q, z) for x in a if x > 0 if x < 10 for q, z in b if q.startswith('i') for y in c if true(y))"
    namespace = Namespace.from_ast(ast.parse(f"import a, b, c\nlist_comp={list_comp_str}\nset_comp={set_comp_str}\ndict_comp={dict_comp_str}\ngen_comp={gen_comp_str}"), location=["namespace"])
    dff_project = DFFProject([namespace], validate=False)

    assert str(namespace["list_comp"]) == list_comp_str
    assert str(namespace["set_comp"]) == set_comp_str
    if version_info >= (3, 9):
        assert str(namespace["dict_comp"]) == dict_comp_str
    else:
        assert str(namespace["dict_comp"]) == "{x: (x ** 2) for q in c if q for x in q if (x > 0)}"
    if version_info >= (3, 9):
        assert str(namespace["gen_comp"]) == "((x, q, z) for x in a if x > 0 if x < 10 for (q, z) in b if q.startswith('i') for y in c if true(y))"
    else:
        assert str(namespace["gen_comp"]) == "((x, q, z) for x in a if (x > 0) if (x < 10) for (q, z) in b if q.startswith('i') for y in c if true(y))"


def test_dependency_extraction():
    namespace1 = Namespace.from_ast(ast.parse("import namespace2\na = namespace2.a"), location=["namespace1"])
    namespace2 = Namespace.from_ast(ast.parse("from namespace3 import c\nimport namespace3\nfrom namespace4 import d\na = print(c[d] + namespace3.j[1])"), location=["namespace2"])
    namespace3 = Namespace.from_ast(ast.parse("c=e\ne={1: 2}\nf=1\nj={1: 2}"), location=["namespace3"])
    namespace4 = Namespace.from_ast(ast.parse("d=1\nq=4\nz=1"), location=["namespace4"])

    dff_project = DFFProject([namespace1, namespace2, namespace3, namespace4], validate=False)

    assert namespace1["a"].dependencies == {
        "namespace1": {"a", "namespace2"},
        "namespace2": {"c", "d", "a", "namespace3"},
        "namespace3": {"c", "e", "j"},
        "namespace4": {"d"},
    }


def test_eq_operator():
    namespace = Namespace.from_ast(ast.parse("import dff.keywords as kw\na = kw.RESPONSE\nb=a"), location=["namespace"])
    dff_project = DFFProject([namespace], validate=False)

    assert "dff.keywords.RESPONSE" == namespace["a"]
    assert namespace['b'] in ["dff.keywords.RESPONSE"]
