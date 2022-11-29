import typing as tp
import ast

from .base_parser_object import BaseParserObject, cached_property, Import, Statement

if tp.TYPE_CHECKING:
    from .dff_project import DFFProject


class Namespace(BaseParserObject):
    def __init__(self, location: tp.List[str], names: tp.Dict[str, BaseParserObject]):
        super().__init__()
        self.location = location
        self.name = ".".join(location)
        for key, value in names.items():
            value.parent = self
            value.append_path = [key]
        self.children = names

    @cached_property
    def namespace(self) -> 'Namespace':
        return self

    @cached_property
    def dff_project(self) -> 'DFFProject':
        return self.parent.dff_project

    def __getitem__(self, item: str):
        return self.children[item]

    def __str__(self) -> str:
        return "\n".join(map(str, self.children.values()))

    def __repr__(self) -> str:
        return f"Namespace(name={self.name}; {'; '.join(map(repr, self.children.values()))})"

    @classmethod
    def from_ast(cls, node: ast.Module, **kwargs) -> 'Namespace':
        children = {}
        for statement in node.body:
            if isinstance(statement, ast.Import):
                imports = Import.from_ast(statement)
                for import_stmt in imports:
                    children[import_stmt.alias or import_stmt.module] = import_stmt
        return cls(names=children, **kwargs)
