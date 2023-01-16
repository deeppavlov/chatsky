"""
Namespace
---------
This module defines `Namespace` -- a class to store contents of python files.
"""
import typing as tp
import ast
from pathlib import Path

from .base_parser_object import BaseParserObject, cached_property, stmt, Statement, Assignment, Import, ImportFrom, Python

if tp.TYPE_CHECKING:
    from dff.utils.parser.dff_project import DFFProject


class Namespace(BaseParserObject):
    """
    This class represents a python file (all the objects defined in it + its location).
    """
    def __init__(self, location: tp.List[str], names: tp.Dict[str, stmt]):
        super().__init__()
        self.children: tp.Dict[str, stmt] = {}
        self.location: tp.List[str] = location
        """Location of the file (as a list of path extensions from `project_root_dir`)"""
        self.name: str = ".".join(location)
        """A name of the file as it would be imported in python (except `__init__` files -- they end with `.__init__`"""
        for key, value in names.items():
            self.add_child(value, key)

    def resolve_relative_import(self, module: str, level: int = 0) -> tp.List[str]:
        """Find a location of a namespace referenced by `level * "." + module` in this namespace

        :param module: Name of the module
        :param level: Relative position of the module
        :return: A location of the module
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
            raise ImportError(f"Cannot import file outside the project_root_dir\nCurrent file location={self.location}\nAttempted import of {module} at level {level}")
        return self.location[:-level] + (stripped_module.split('.') if stripped_module != "" else [])

    @cached_property
    def namespace(self) -> 'Namespace':
        return self

    @cached_property
    def dff_project(self) -> 'DFFProject':
        if self.parent is None:
            raise RuntimeError(f"Parent is not set: {repr(self)}")
        return self.parent.dff_project

    def get_object(self, item: str):
        """Return an object by its name. If the object is of type `Assignment` return its value
        """
        obj = self.children.get(item)
        if isinstance(obj, Assignment):
            return obj.children["value"]
        return obj

    def __getitem__(self, item: str):
        """Return an object by its name. If the object is of type `Assignment` return its value
        :raises KeyError:
            Object not found
        """
        obj = self.children[item]
        if isinstance(obj, Assignment):
            return obj.children["value"]
        return obj

    @staticmethod
    def dump_statements(statements: tp.List[stmt]) -> str:
        """A method for dumping a list of statements. Inserts newlines between statements in the following amount:
            - If any of the two neighboring statements is `Def` -- 3 new lines
            - If both neighboring statements are :py:class:`~.Import` or :py:class:`.~ImportFrom` -- 1 new line
            - Otherwise, 2 new lines.

        :param statements: A list of statements to dump
        :return: Dumps of the statements separated by an appropriate amount of new lines
        """
        def get_newline_count(statement: stmt):
            if isinstance(statement, (Import, ImportFrom)):
                return 1
            if isinstance(statement, Python) and statement.type.endswith("Def"):  # function and class defs
                return 3
            return 2
        if len(statements) == 0:
            return "\n"

        result = [statements[0].dump()]
        previous_stmt = statements[0]
        for current_stmt in statements[1:]:
            result.append(max(get_newline_count(previous_stmt), get_newline_count(current_stmt)) * "\n")
            result.append(current_stmt.dump())
            previous_stmt = current_stmt
        return "".join(result) + "\n"

    def dump(self, current_indent=0, indent=4, object_filter: tp.Set[str] = None) -> str:
        return self.dump_statements([value for key, value in self.children.items() if object_filter is None or key in object_filter])

    def get_imports(self) -> tp.List[tp.List[str]]:
        """Return a list of imported modules (represented by their locations)
        """
        imports = []
        for statement in self.children.values():
            if isinstance(statement, Import):
                imports.append(self.resolve_relative_import(statement.module))
            if isinstance(statement, ImportFrom):
                imports.append(self.resolve_relative_import(statement.module, statement.level))
        return imports

    @classmethod
    def from_ast(cls, node: ast.Module, **kwargs) -> 'Namespace':
        children = {}
        for statement in node.body:
            statements = Statement.from_ast(statement)
            if isinstance(statements, dict):
                children.update(statements)
        return cls(names=children, **kwargs)

    @classmethod
    def from_file(cls, project_root_dir: Path, file: Path):
        """Construct the Namespace from a python file.

        :param project_root_dir: A root dir of the dff project. All local files should be inside this dir
        :param file: A `.py` file to construct the namespace from
        :return: A Namespace of the file
        """
        location = list(file.with_suffix("").relative_to(project_root_dir).parts)
        with open(file, "r", encoding="utf-8") as fd:
            return Namespace.from_ast(ast.parse(fd.read()), location=location)

