"""
This module defines parser objects -- nodes that form a tree.
"""
import typing as tp
from abc import ABC, abstractmethod
import ast

try:
    from functools import cached_property
except ImportError:
    from cached_property import cached_property  # todo: remove this when python3.7 support is dropped

try:
    from ast import unparse
except ImportError:
    from astunparse import unparse  # todo: remove this when python3.8 support is dropped

try:
    remove_suffix = str.removesuffix
    remove_prefix = str.removeprefix
except AttributeError:
    from .utils import remove_prefix, remove_suffix


if tp.TYPE_CHECKING:
    from .namespace import Namespace
from .exceptions import KeyNotFound, StarError


KeywordDict = tp.Dict[str, tp.Union['BaseParserObject', 'KeywordDict']]


class BaseParserObject(ABC):
    """
    An interface for the other parser objects.

    :param parent: Parent node
    :type parent: :py:class:`.BaseParserObject`
    :param child_paths: Mapping from child `id`s to their path relative to `self`
    :type child_paths: dict[int, list[str]]
    :param children: Mapping from
    """
    def __init__(self):
        self.parent: tp.Optional[BaseParserObject] = None
        self.append_path: tp.List[str] = []
        self.children: KeywordDict = {}

    def resolve_path(self, path: tp.List[str]) -> 'BaseParserObject':
        if len(path) == 0:
            return self
        current_dict = self.children
        for index, key in enumerate(path, start=1):
            item = current_dict.get(key)
            if item is None:
                raise KeyNotFound(f"Not found key {key} in {current_dict}\nObject: {repr(self)}")
            if isinstance(item, BaseParserObject):
                return item.resolve_path(path[index:])
            else:
                current_dict = item
        raise KeyNotFound(f"Not found {path} in {self.children}\nObject: {repr(self)}")

    @cached_property
    def path(self) -> tp.List[str]:
        if self.parent is None:
            raise RuntimeError(f"Parent is not set: {repr(self)}")
        return self.parent.path + self.append_path

    @cached_property
    def namespace(self) -> 'Namespace':
        if self.parent is None:
            raise RuntimeError(f"Parent is not set: {repr(self)}")
        if isinstance(self.parent, Namespace):
            return self.parent
        else:
            return self.parent.namespace

    @abstractmethod
    def __repr__(self):
        ...

    @abstractmethod
    def __str__(self):
        ...

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        if isinstance(other, BaseParserObject):
            return repr(self) == repr(other)
        return False

    @classmethod
    @abstractmethod
    def from_ast(cls, node) -> 'BaseParserObject':
        if isinstance(node, ast.Dict):
            return Dict.from_ast(node)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return String.from_ast(node)
        return Python.from_ast(node)


class ReferenceObject(BaseParserObject, ABC):
    @cached_property
    @abstractmethod
    def resolve_self(self) -> BaseParserObject:
        ...

    def __hash__(self):
        return hash(self.resolve_self)

    def __eq__(self, other):
        if isinstance(other, ReferenceObject):
            return self.resolve_self == other.resolve_self
        return self.resolve_self == other


class String(BaseParserObject):
    def __init__(self, string: str):
        super().__init__()
        self.string = string

    def __str__(self):
        return repr(self.string)

    def __repr__(self):
        return f"String({self.string})"

    @classmethod
    def from_ast(cls, node: ast.Constant) -> 'BaseParserObject':
        if not isinstance(node.value, str):
            raise RuntimeError(f"Node {node} is not str")
        return cls(node.value)


class Python(BaseParserObject):
    def __init__(self, string: str):
        super().__init__()
        self.string = string

    def __str__(self):
        return self.string

    def __repr__(self):
        return f"Python({self.string})"

    @classmethod
    def from_ast(cls, node: ast.AST) -> 'BaseParserObject':
        return cls(remove_suffix(unparse(node), "\n"))


class Dict(BaseParserObject):
    def __init__(self, dictionary: tp.Dict[BaseParserObject, BaseParserObject]):
        super().__init__()
        self.keys: tp.Dict[BaseParserObject, str] = {}
        for key, value in dictionary.items():
            key.parent = self
            value.parent = self
            key.append_path = [repr(key), "key"]
            value.append_path = [repr(key), "value"]
            self.keys[key] = repr(key)
            self.children[repr(key)] = {}
            self.children[repr(key)]["key"] = key
            self.children[repr(key)]["value"] = value

    def __str__(self):
        return "{" + ", ".join(
            [f"{str(value['key'])}: {str(value['value'])}" for value in self.children.values()]
        ) + "}"

    def __repr__(self):
        return "Dict(" + ", ".join(
            [f"{repr(value['key'])}: {repr(value['value'])}" for value in self.children.values()]
        ) + ")"

    def __getitem__(self, item: tp.Union[BaseParserObject, str]):
        if isinstance(item, BaseParserObject):
            key = self.keys[item]
            return self.children[key]["value"]
        elif isinstance(item, str):
            dict_item = self.children[item]
            return dict_item["value"]
        else:
            raise TypeError(f"Item {repr(item)} is not `BaseParserObject` nor `str")

    @classmethod
    def from_ast(cls, node: ast.Dict) -> BaseParserObject:
        result = {}
        for key, value in zip(node.keys, node.values):
            if key is None:
                raise StarError(f"Dict comprehensions are not supported: {unparse(node)}")
            result[BaseParserObject.from_ast(key)] = BaseParserObject.from_ast(value)
        return cls(result)



# class Call(BaseParserObject):
#     def __init__(
#         self,
#         name: BaseParserObject,
#         args: tp.List[BaseParserObject],
#         keywords: tp.Dict[str, BaseParserObject]
#     ):
#         super(Call, self).__init__()
#         name.parent = self
#         self.child_paths[id(name)] =
#         self.name = name
