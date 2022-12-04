import typing as tp
import ast
from pathlib import Path

from .base_parser_object import BaseParserObject, cached_property, Statement, Assignment, Import, ImportFrom

if tp.TYPE_CHECKING:
    from .dff_project import DFFProject


class Namespace(BaseParserObject):
    def __init__(self, location: tp.List[str], names: tp.Dict[str, Statement]):
        super().__init__()
        self.children: tp.Dict[str, Statement]
        self.location = location
        self.name = ".".join(location)
        for key, value in names.items():
            self.add_child(value, key)

    def resolve_relative_import(self, module: str, level: int = 0) -> tp.List[str]:
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

    def __getitem__(self, item: str):
        obj = self.children[item]
        if isinstance(obj, Assignment):
            return obj.children["value"]
        return obj

    def __str__(self) -> str:
        return "\n".join(map(str, self.children.values()))

    def __repr__(self) -> str:
        return f"Namespace(name={self.name}; {'; '.join(map(repr, self.children.values()))})"

    def get_imports(self) -> tp.List[tp.List[str]]:
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
            children.update(Statement.from_ast(statement))
        return cls(names=children, **kwargs)

    @classmethod
    def from_file(cls, project_root_dir: Path, file: Path):
        location = list(file.with_suffix("").relative_to(project_root_dir).parts)
        with open(file, "r", encoding="utf-8") as fd:
            return Namespace.from_ast(ast.parse(fd.read()), location=location)

