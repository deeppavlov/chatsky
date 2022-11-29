import typing as tp

from .base_parser_object import BaseParserObject, cached_property

if tp.TYPE_CHECKING:
    from .namespace import Namespace


class DFFProject(BaseParserObject):
    def __init__(self, namespaces: tp.List['Namespace']):
        super().__init__()
        for namespace in namespaces:
            namespace.parent = self
            namespace.append_path = [namespace.name]
            self.children[namespace.name] = namespace

    @cached_property
    def path(self) -> tp.List[str]:
        return []

    @cached_property
    def namespace(self) -> 'Namespace':
        raise RuntimeError(f"DFFProject does not have a `namespace` attribute\n{repr(self)}")

    @cached_property
    def dff_project(self) -> 'DFFProject':
        return self

    def __str__(self) -> str:
        return "\n".join(map(str, self.children.values()))

    def __repr__(self) -> str:
        return f"DFFProject({'; '.join(map(repr, self.children.values()))})"

    @classmethod
    def from_ast(cls, node, **kwargs):
        raise NotImplementedError()
