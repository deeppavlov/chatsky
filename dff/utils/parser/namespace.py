"""
Namespace
---------
This module defines a :py:class:`~.Namespace` class.

Its children attribute stores all statements defined inside a single python file.
"""
import typing as tp
import ast
from pathlib import Path

from dff.utils.parser.base_parser_object import (
    BaseParserObject,
    cached_property,
    Statement,
    Assignment,
    Import,
    ImportFrom,
    Python,
)

if tp.TYPE_CHECKING:
    from dff.utils.parser.dff_project import DFFProject


class Namespace(BaseParserObject):
    """
    This class represents a python file.
    It stores all the statements / expressions defined in a file as well as the location of that file relative to
    `project_root_dir`.
    """

    def __init__(self, location: tp.List[str], names: tp.Dict[str, Statement]):
        BaseParserObject.__init__(self)
        self.children: tp.MutableMapping[str, Statement] = {}
        self.location: tp.List[str] = location
        """Location of the file (as a list of path extensions from `project_root_dir`)"""
        self.name: str = ".".join(location)
        """A name of the file as it would be imported in python (except `__init__` files -- they end with `.__init__`"""
        for key, value in names.items():
            self.add_child(value, key)

    def resolve_relative_import(self, module: str, level: int = 0) -> str:
        """
        Find a location of a namespace referenced by `level * "." + module` in this namespace.

        :param module: Name of the module.
        :param level: Relative position of the module.
        :return: A location of the module (a string representing path to the module separated by dots).
        """
        stripped_module = module.lstrip(".")
        leading_dots = len(module) - len(stripped_module)
        if leading_dots != 0:
            if level == 0:
                level = leading_dots
            else:
                raise RuntimeError(f"Level is set but module contains leading dots: module={module}, level={level}")
        if level == 0:
            level = 1
        if level > len(self.location):
            raise ImportError(
                f"Cannot import file outside the project_root_dir\n"
                f"Current file location={self.location}\nAttempted import of {module} at level {level}"
            )
        return ".".join(self.location[:-level] + ([stripped_module] if stripped_module else []))

    @cached_property
    def namespace(self) -> "Namespace":
        return self

    @cached_property
    def dff_project(self) -> "DFFProject":
        if self.parent is None:
            raise RuntimeError(f"Parent is not set: {repr(self)}")
        return self.parent.dff_project

    def get_object(self, item: str):
        """Return an object by its name. If the object is of type `Assignment` return its value."""
        obj = self.children.get(item)
        if isinstance(obj, Assignment):
            return obj.children["value"]
        return obj

    def __getitem__(self, item: str):
        """
        Return an object by its name. If the object is of type `Assignment` return its value.
        :raises KeyError:
            Object not found.
        """
        obj = self.children[item]
        if isinstance(obj, Assignment):
            return obj.children["value"]
        return obj

    @staticmethod
    def dump_statements(statements: tp.List[Statement], current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        """
        A method for dumping a list of statements. Inserts newlines between statements in the following amount:

        - If any of the two neighboring statements is `Def` -- 3 new lines.
        - If both neighboring statements are :py:class:`~.Import` or :py:class:`.~ImportFrom` -- 1 new line.
        - Otherwise, 2 new lines.

        :param statements: A list of statements to dump.
        :param current_indent: Current indentation level (in whitespace number), defaults to 0.
        :param indent:
            Indentation increment (in whitespace number), defaults to 4.
            If set to None, all statements will be printed in one line (except for unsupported statements).
        :return: Dumps of the statements separated by an appropriate amount of new lines.
        """

        def get_newline_count(statement: Statement):
            if isinstance(statement, (Import, ImportFrom)):
                return 1
            if isinstance(statement, Python) and statement.type.endswith("Def"):  # function and class defs
                return 3
            return 2

        if len(statements) == 0:
            return "\n"

        result = [statements[0].dump(current_indent, indent)]
        previous_stmt = statements[0]
        for current_stmt in statements[1:]:
            result.append(max(get_newline_count(previous_stmt), get_newline_count(current_stmt)) * "\n")
            result.append(current_indent * " " + current_stmt.dump(current_indent, indent))
            previous_stmt = current_stmt
        return "".join(result) + "\n"

    def dump(
        self, current_indent: int = 0, indent: tp.Optional[int] = 4, object_filter: tp.Optional[tp.Set[str]] = None
    ) -> str:
        """
        Dump all statements in the namespace.

        :param current_indent: Current indentation level (in whitespace number), defaults to 0.
        :param indent:
            Indentation increment (in whitespace number), defaults to 4.
            If set to None, all statements will be printed in one line (except for unsupported statements).
        :param object_filter:
            A set of object names. If specified, only objects specified in the filter will be dumped.
            Defaults to None.
        :return: Representation of the namespace as a string.
        """
        return self.dump_statements(
            [value for key, value in self.children.items() if object_filter is None or key in object_filter],
            current_indent,
            indent,
        )

    def get_imports(self) -> tp.List[str]:
        """Return a list of imported modules (represented by their locations)."""
        imports = []
        for statement in self.children.values():
            if isinstance(statement, Import):
                imports.append(self.resolve_relative_import(statement.module))
            if isinstance(statement, ImportFrom):
                imports.append(self.resolve_relative_import(statement.module, statement.level))
        return imports

    @classmethod
    def from_ast(cls, node: ast.Module, **kwargs) -> "Namespace":  # type: ignore
        """
        Construct Namespace from :py:class:`ast.Module`.

        For each statement in the module:

        - If it is supported by any :py:class:`~.Statement`, all objects extracted from the statement will be added to
          the namespace under their names.
        - Otherwise a :py:class:`~.Python` object is added under a string representation of the count of python
          objects added to the namespace so far.

        For example, there is currently no :py:class:`~.Statement` that supports function definitions and
        if one is present in `node`, its (key, value) pair will be `("0", Python(def ...))`.
        """
        children = {}
        python_counter = 0
        for statement in node.body:
            statements = Statement.auto(statement)
            if isinstance(statements, dict):
                children.update(statements)
            elif isinstance(statements, Python):
                children[str(python_counter)] = statements
                python_counter += 1
        return cls(names=children, **kwargs)

    @classmethod
    def from_file(cls, project_root_dir: Path, file: Path):
        """
        Construct a Namespace from a python file.

        For each statement in the file:

        - If it is supported by any :py:class:`~.Statement`, all objects extracted from the statement will be added to
          the namespace under their names.
        - Otherwise a :py:class:`~.Python` object is added under a string representation of the count of python
          objects added to the namespace so far.

        For example, there is currently no :py:class:`~.Statement` that supports function definitions and
        if one is present in `file`, its (key, value) pair will be `("0", Python(def ...))`.

        :param project_root_dir: A root dir of the dff project. All project files should be inside this dir.
        :param file: A `.py` file to construct the namespace from.
        :return: A Namespace of the file.
        """
        location = list(file.with_suffix("").relative_to(project_root_dir).parts)
        with open(file, "r", encoding="utf-8") as fd:
            return Namespace.from_ast(ast.parse(fd.read()), location=location)
