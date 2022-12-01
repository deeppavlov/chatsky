import typing as tp
from pathlib import Path
import logging

from .base_parser_object import BaseParserObject, cached_property
from .namespace import Namespace


logger = logging.getLogger(__name__)


class DFFProject(BaseParserObject):
    def __init__(self, namespaces: tp.List['Namespace']):
        super().__init__()
        for namespace in namespaces:
            self.add_child(namespace, namespace.name)

    def __getitem__(self, item: tp.Union[tp.List[str], str]):
        if isinstance(item, str):
            return self.children[item]
        elif isinstance(item, list):
            if item[-1] == "__init__":
                return self.children[".".join(item)]
            namespace = self.children.get(".".join(item))
            if namespace is None:
                return self.children[".".join(item) + ".__init__"]
            return namespace
        raise TypeError(f"{type(item)}")

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

    @classmethod
    def from_python(cls, project_root_dir: Path, entry_point: Path):
        namespaces = {}
        if not project_root_dir.exists():
            raise RuntimeError(f"Path does not exist: {project_root_dir}")

        def _process_file(file: Path):
            if not file.exists():
                raise RuntimeError(f"File {file} does not exist in {project_root_dir}")
            namespace = Namespace.from_file(project_root_dir, file)
            namespaces[namespace.name] = namespace

            for imported_file in namespace.get_imports():
                if ".".join(imported_file) not in namespaces.keys():
                    path = project_root_dir.joinpath(*imported_file).with_suffix(".py")
                    if path.exists():
                        _process_file(path)

        _process_file(entry_point)
        return cls(list(namespaces.values()))
