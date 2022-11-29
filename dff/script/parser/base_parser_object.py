"""
This module defines parser objects -- nodes that form a tree.
"""
import typing as tp
from abc import ABC, abstractmethod
import ast
import logging

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
    from .utils import remove_prefix, remove_suffix  # todo: remove this when python3.8 support is dropped


if tp.TYPE_CHECKING:
    from .namespace import Namespace
    from .dff_project import DFFProject
from .exceptions import KeyNotFound, StarError


logger = logging.getLogger(__name__)

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
        return self.parent.namespace

    @cached_property
    def dff_project(self) -> 'DFFProject':
        return self.namespace.dff_project

    @abstractmethod  # todo: add dump function, repr calls it with certain params
    def __repr__(self) -> str:
        ...

    @abstractmethod
    def __str__(self) -> str:
        ...

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        if isinstance(other, BaseParserObject):
            return repr(self) == repr(other)
        return False

    @classmethod
    @abstractmethod
    def from_ast(cls, node, **kwargs):
        ...


class Statement(BaseParserObject, ABC):
    """
    This class is for nodes that represent [statements](https://docs.python.org/3.10/library/ast.html#statements)
    """
    @classmethod
    @abstractmethod
    def from_ast(cls, node, **kwargs) -> tp.List['Statement']:
        ...


class Expression(BaseParserObject, ABC):
    """
    This class is for nodes that represent [expressions](https://docs.python.org/3.10/library/ast.html#expressions)
    """
    @classmethod
    @abstractmethod
    def from_ast(cls, node, **kwargs) -> 'Expression':
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
        """

        :return: Self, if can't resolve
        """
        ...

    def __hash__(self):
        return hash(self.resolve_self)

    def __eq__(self, other):
        if isinstance(other, ReferenceObject):
            return self.resolve_self == other.resolve_self
        return self.resolve_self == other


class Import(Statement, ReferenceObject):
    def __init__(self, module: str, alias: tp.Optional[str] = None):
        Statement.__init__(self)
        ReferenceObject.__init__(self)
        self.module = module
        self.alias = alias

    def __str__(self):
        return f"import {self.module}" + f" as {self.alias}" if self.alias else ""

    def __repr__(self):
        return f"Import(module={self.module}, alias={self.alias})"

    @cached_property
    def resolve_self(self) -> BaseParserObject:
        try:
            return self.dff_project.resolve_path([self.namespace.name.rpartition(".")[0] + self.module])
        except KeyNotFound as error:
            logger.debug(f"Import did not resolve: {repr(self)}.\nReason: {error}")
            return self

    @classmethod
    def from_ast(cls, node: ast.Import, **kwargs) -> tp.List['Import']:
        result = []
        for name in node.names:
            result.append(cls(name.name, name.asname))
        return result


class String(Expression):
    def __init__(self, string: str):
        super().__init__()
        self.string = string

    def __str__(self):
        return repr(self.string)

    def __repr__(self):
        return f"String({self.string})"

    @classmethod
    def from_ast(cls, node: ast.Constant, **kwargs) -> 'String':
        if not isinstance(node.value, str):
            raise RuntimeError(f"Node {node} is not str")
        return cls(node.value)


class Python(Expression):
    def __init__(self, string: str):
        super().__init__()
        self.string = string

    def __str__(self):
        return self.string

    def __repr__(self):
        return f"Python({self.string})"

    @classmethod
    def from_ast(cls, node: ast.AST, **kwargs) -> 'Python':
        return cls(remove_suffix(unparse(node), "\n"))


class Dict(Expression):
    def __init__(self, dictionary: tp.Dict[Expression, Expression]):
        super().__init__()
        self.keys: tp.Dict[Expression, str] = {}
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

    def __getitem__(self, item: tp.Union[Expression, str]):
        if isinstance(item, Expression):
            key = self.keys[item]
            return self.children[key]["value"]
        elif isinstance(item, str):
            dict_item = self.children[item]
            return dict_item["value"]
        else:
            raise TypeError(f"Item {repr(item)} is not `BaseParserObject` nor `str")

    @classmethod
    def from_ast(cls, node: ast.Dict, **kwargs) -> 'Dict':
        result = {}
        for key, value in zip(node.keys, node.values):
            if key is None:
                raise StarError(f"Dict comprehensions are not supported: {unparse(node)}")
            result[Expression.from_ast(key)] = Expression.from_ast(value)
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
