import typing as tp
import ast

from .base_parser_object import BaseParserObject, cached_property, Statement, Assignment

if tp.TYPE_CHECKING:
    from .dff_project import DFFProject


class Namespace(BaseParserObject):
    def __init__(self, location: tp.List[str], names: tp.Dict[str, BaseParserObject]):
        super().__init__()
        self.location = location
        self.name = ".".join(location)
        for key, value in names.items():
            value.parent = self
            value.append_path = key
        self.children = names

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

    @classmethod
    def from_ast(cls, node: ast.Module, **kwargs) -> 'Namespace':
        children = {}
        for statement in node.body:
            children.update(Statement.from_ast(statement))
        return cls(names=children, **kwargs)
