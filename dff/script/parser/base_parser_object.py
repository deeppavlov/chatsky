"""
This module defines parser objects -- nodes that form a tree.
"""
import typing as tp
from abc import ABC, abstractmethod
from collections.abc import Iterable
from collections import defaultdict
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
from .exceptions import StarError
from .utils import is_instance


logger = logging.getLogger(__name__)


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
        self.append_path: tp.Optional[str] = None
        self.children: tp.Dict[str, BaseParserObject] = {}

    @cached_property
    def dependencies(self) -> tp.Dict[str, tp.Set[str]]:
        result: tp.DefaultDict[str, tp.Set[str]] = defaultdict(set)
        if len(self.path) >= 2:
            result[self.path[0]].add(self.path[1])
        else:  # self is a Namespace
            return result

        if isinstance(self, ReferenceObject):
            resolved = self.resolve_self
            if resolved is not None:
                for namespace, objects in resolved.dependencies.items():
                    result[namespace].update(objects)

        for child in self.children.values():
            for namespace, objects in child.dependencies.items():
                result[namespace].update(objects)
        return result

    def add_child(self, child: 'BaseParserObject', asname: str):
        child.parent = self
        child.append_path = asname
        self.children[asname] = child

    def resolve_path(self, path: tp.Tuple[str, ...]) -> 'BaseParserObject':
        if len(path) == 0:
            return self
        current_dict = self.children
        for index, key in enumerate(path, start=1):
            item = current_dict.get(key)
            if item is None:
                raise KeyError(f"Not found key {key} in {current_dict}\nObject: {repr(self)}")
            return item.resolve_path(path[index:])
        raise KeyError(f"Not found {path} in {self.children}\nObject: {repr(self)}")

    @cached_property
    def path(self) -> tp.Tuple[str, ...]:
        if self.parent is None:
            raise RuntimeError(f"Parent is not set: {repr(self)}")
        return self.parent.path + ((self.append_path, ) if self.append_path else ())

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
        return hash(str(self))

    def __eq__(self, other):
        if isinstance(other, BaseParserObject):
            return str(self) == str(other)
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented

    @classmethod
    @abstractmethod
    def from_ast(cls, node, **kwargs):
        ...


class Statement(BaseParserObject, ABC):
    """
    This class is for nodes that represent [statements](https://docs.python.org/3.10/library/ast.html#statements)
    """
    def __init__(self):
        BaseParserObject.__init__(self)
        self.children: tp.Dict[str, Expression]

    @classmethod
    @abstractmethod
    def from_ast(cls, node, **kwargs) -> tp.Dict[str, 'Statement']:
        if isinstance(node, ast.Import):
            return Import.from_ast(node)
        if isinstance(node, ast.ImportFrom):
            return ImportFrom.from_ast(node)
        if isinstance(node, ast.Assign):
            return Assignment.from_ast(node)
        if isinstance(node, ast.AnnAssign):
            if node.value is not None:
                return Assignment.from_ast(node)
        return {}


class Expression(BaseParserObject, ABC):
    """
    This class is for nodes that represent [expressions](https://docs.python.org/3.10/library/ast.html#expressions)
    """
    def __init__(self):
        BaseParserObject.__init__(self)
        self.children: tp.Dict[str, 'Expression']

    @classmethod
    @abstractmethod
    def from_ast(cls, node, **kwargs) -> 'Expression':
        if isinstance(node, ast.Call):
            return Call.from_ast(node)
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return Iterable.from_ast(node)
        if isinstance(node, ast.Subscript):
            # todo: remove the right part when python3.8 support is dropped
            if not (isinstance(node.slice, ast.Slice) or is_instance(node.slice, "_ast.ExtSlice")):
                return Subscript.from_ast(node)
        if isinstance(node, ast.Name):
            return Name.from_ast(node)
        if isinstance(node, ast.Attribute):
            return Attribute.from_ast(node)
        if isinstance(node, ast.Dict):
            return Dict.from_ast(node)
        # todo: replace this with isinstance when python3.7 support is dropped
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return String.from_ast(node)
        if is_instance(node, "_ast.Str"):  # todo: remove this when python3.7 support is dropped
            return String.from_ast(node)
        return Python.from_ast(node)


class ReferenceObject(BaseParserObject, ABC):
    def __init__(self):
        BaseParserObject.__init__(self)

    @cached_property
    @abstractmethod
    def resolve_self(self) -> tp.Optional[BaseParserObject]:
        """

        :return: None, if can't resolve
        """
        ...

    @cached_property
    def absolute(self) -> tp.Optional[BaseParserObject]:  # todo: handle recursion
        """
        Return an absolute object --  if the current object is a reference to another reference that reference will
        be resolved as well.
        """
        resolved = self.resolve_self
        if isinstance(resolved, ReferenceObject):
            return resolved.absolute
        return resolved

    @cached_property
    @abstractmethod
    def resolve_name(self) -> BaseParserObject:
        """
        Same as `absolute` but instead of returning None at failed resolution returns the name of the absolute object
        """
        ...

    def __hash__(self):
        return BaseParserObject.__hash__(self.resolve_name)

    def __eq__(self, other):
        if isinstance(other, ReferenceObject):
            return BaseParserObject.__eq__(self.resolve_name, other.resolve_name)
        return BaseParserObject.__eq__(self.resolve_name, other)


class Import(Statement, ReferenceObject):
    def __init__(self, module: str, alias: tp.Optional[str] = None):
        Statement.__init__(self)
        ReferenceObject.__init__(self)
        self.module = module
        self.alias = alias

    def __str__(self):
        return f"import {self.module}" + (f" as {self.alias}" if self.alias else "")

    def __repr__(self):
        return f"Import(module={self.module}, alias={self.alias})"

    @cached_property
    def resolve_self(self) -> tp.Optional[BaseParserObject]:
        try:
            return self.dff_project[".".join(self.namespace.resolve_relative_import(self.module))]
        except KeyError as error:
            logger.warning(f"{self.__class__.__name__} did not resolve: {repr(self)}\nKeyError: {error}")
            return None

    @cached_property
    def resolve_name(self) -> tp.Optional[BaseParserObject]:
        return self.absolute or Expression.from_ast(ast.parse(self.module).body[0].value)

    @classmethod
    def from_ast(cls, node: ast.Import, **kwargs) -> tp.Dict[str, 'Import']:
        result = {}
        for name in node.names:
            result[name.asname or name.name] = cls(name.name, name.asname)
        return result


class ImportFrom(Statement, ReferenceObject):
    def __init__(self, module: str, level: int, obj: str, alias: tp.Optional[str] = None):
        Statement.__init__(self)
        ReferenceObject.__init__(self)
        self.module = module
        self.level = level
        self.obj = obj
        self.alias = alias

    def __str__(self):
        return f"from {self.level * '.' + self.module} import {self.obj}" + (f" as {self.alias}" if self.alias else "")

    def __repr__(self):
        return f"ImportFrom(module={self.module}, level={self.level}, obj={self.obj}, alias={self.alias})"

    @cached_property
    def resolve_self(self) -> tp.Optional[BaseParserObject]:
        try:
            return self.dff_project[self.namespace.resolve_relative_import(self.module, self.level)][self.obj]
        except KeyError as error:
            logger.warning(f"{self.__class__.__name__} did not resolve: {repr(self)}\nKeyError: {error}")
            return None

    @cached_property
    def resolve_name(self) -> tp.Optional[BaseParserObject]:
        resolved = self.resolve_self
        if isinstance(resolved, ReferenceObject):
            resolved = resolved.resolve_name
        return resolved or Expression.from_ast(ast.parse(self.module + "." + self.obj).body[0].value)

    @classmethod
    def from_ast(cls, node: ast.ImportFrom, **kwargs) -> tp.Dict[str, 'ImportFrom']:
        result = {}
        for name in node.names:
            if name.name == '*':
                raise StarError(f"Starred import is not supported: {unparse(node)}")
            result[name.asname or name.name] = cls(node.module or "", node.level, name.name, name.asname)
        return result


class Assignment(Statement):
    def __init__(self, target: Expression, value: Expression):
        super().__init__()
        self.add_child(target, "target")
        self.add_child(value, "value")

    def __str__(self):
        return f"{str(self.children['target'])} = {str(self.children['value'])}"

    def __repr__(self):
        return f"Assignment(target={repr(self.children['target'])}; value={repr(self.children['value'])}"

    @classmethod
    def from_ast(cls, node, **kwargs) -> tp.Dict[str, 'Assignment']:
        result = {}
        if isinstance(node, ast.Assign):
            target = Expression.from_ast(node.targets[-1])
            result[str(target)] = cls(target=target, value=Expression.from_ast(node.value))
            for target in node.targets[:-1]:
                target = Expression.from_ast(target)  # todo: add support for tuple targets
                result[str(target)] = cls(target=target, value=Expression.from_ast(node.targets[-1]))
        if isinstance(node, ast.AnnAssign):
            if node.value is None:
                raise RuntimeError(f"Assignment has no value: {node}")
            target = Expression.from_ast(node.target)
            result[str(target)] = cls(target=target, value=Expression.from_ast(node.value))
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
    def from_ast(cls, node: tp.Union['ast.Str', ast.Constant], **kwargs) -> 'String':
        if is_instance(node, "_ast.Str"):  # todo: remove this when python3.7 support is dropped
            return cls(node.s)
        elif isinstance(node, ast.Constant):
            return cls(node.value)
        raise RuntimeError(f"Node {node} is not str")


class Python(Expression):
    def __init__(self, node: ast.AST):
        super().__init__()
        for key, value in node.__dict__.items():
            if isinstance(value, ast.expr):
                self.add_child(Expression.from_ast(value), key)
        self.string = remove_suffix(unparse(node), "\n")

    def __str__(self):
        return self.string

    def __repr__(self):
        return f"Python({self.string})"

    @classmethod
    def from_str(cls, string: str) -> 'Python':
        return cls(ast.parse(string).body[0].value)

    @classmethod
    def from_ast(cls, node: ast.AST, **kwargs) -> 'Python':
        return cls(node)


class Dict(Expression):
    def __init__(self, keys: tp.List[Expression], values: tp.List[Expression]):
        super().__init__()
        self.__keys: tp.List[tp.Tuple[Expression, str]] = []
        for key, value in zip(keys, values):
            self.__keys.append((key, repr(key)))
            self.add_child(key, repr(key) + "key")
            self.add_child(value, repr(key) + "value")

    def key_by_value(self, value: Expression) -> Expression:
        return self.children[remove_suffix(value.append_path, "value") + "key"]

    def keys(self) -> tp.Iterator[Expression]:
        for _, key_str in self.__keys:
            yield self.children[key_str + "key"]

    def values(self) -> tp.Iterator[Expression]:
        for _, key_str in self.__keys:
            yield self.children[key_str + "value"]

    def items(self) -> tp.Iterator[tp.Tuple[Expression, Expression]]:
        for _, key_str in self.__keys:
            yield self.children[key_str + "key"], self.children[key_str + "value"]

    @cached_property
    def _keys(self) -> tp.Dict[Expression, str]:
        result = {}
        for key, value in self.__keys:
            result[key] = value
        return result

    def __str__(self):
        return "{" + ", ".join(
            [f"{str(self.children[key + 'key'])}: {str(self.children[key + 'value'])}" for key in self._keys.values()]
        ) + "}"

    def __repr__(self):
        return "Dict(" + ", ".join(
            [
                f"{repr(self.children[key + 'key'])}: "
                f"{repr(self.children[key + 'value'])}" for key in self._keys.values()
            ]
        ) + ")"

    def __getitem__(self, item: tp.Union[Expression, str]):
        if isinstance(item, Expression):
            key = self._keys[item]
            return self.children[key + "value"]
        elif isinstance(item, str):
            return self.children[item + "value"]
        else:
            raise TypeError(f"Item {repr(item)} is not `BaseParserObject` nor `str")

    @classmethod
    def from_ast(cls, node: ast.Dict, **kwargs) -> 'Dict':
        keys, values = [], []
        for key, value in zip(node.keys, node.values):
            if key is None:
                raise StarError(f"Dict comprehensions are not supported: {unparse(node)}")
            keys.append(Expression.from_ast(key))
            values.append(Expression.from_ast(value))
        return cls(keys,values)


class Name(Expression, ReferenceObject):
    def __init__(self, name: str):
        Expression.__init__(self)
        ReferenceObject.__init__(self)
        self.name = name

    @cached_property
    def resolve_self(self) -> tp.Optional[BaseParserObject]:
        try:
            return self.namespace[self.name]
        except KeyError as error:
            logger.warning(f"{self.__class__.__name__} did not resolve: {repr(self)}\nKeyError: {error}")
            return None

    @cached_property
    def resolve_name(self) -> tp.Optional[BaseParserObject]:
        resolved = self.resolve_self
        if isinstance(resolved, ReferenceObject):
            return resolved.resolve_name
        return resolved or self

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Name({self.name})"

    @classmethod
    def from_ast(cls, node: ast.Name, **kwargs) -> 'Expression':
        return cls(node.id)


class Attribute(Expression, ReferenceObject):
    def __init__(self, value: Expression, attr: str):
        Expression.__init__(self)
        ReferenceObject.__init__(self)
        self.add_child(value, "value")
        self.attr = attr

    @cached_property
    def resolve_self(self) -> tp.Optional[BaseParserObject]:
        value = self.children["value"]
        if isinstance(value, ReferenceObject):
            value = value.absolute
        try:
            if is_instance(value, "dff.script.parser.namespace.Namespace"):
                return value[self.attr]
        except KeyError as error:
            logger.warning(f"{self.__class__.__name__} did not resolve: {repr(self)}\nKeyError: {error}")
        return None

    @cached_property
    def resolve_name(self) -> tp.Optional[BaseParserObject]:
        value = self.children["value"]
        if isinstance(value, ReferenceObject):
            value = value.resolve_name
        return self.resolve_self or Attribute(value, self.attr)

    def __str__(self):
        return str(self.children["value"]) + "." + self.attr

    def __repr__(self):
        return f"Attribute(value={repr(self.children['value'])}; attr={self.attr})"

    @classmethod
    def from_ast(cls, node: ast.Attribute, **kwargs) -> 'Expression':
        return cls(Expression.from_ast(node.value), node.attr)


class Subscript(Expression, ReferenceObject):
    def __init__(self, value: Expression, index: Expression):
        Expression.__init__(self)
        ReferenceObject.__init__(self)
        self.add_child(value, "value")
        self.add_child(index, "index")

    @cached_property
    def resolve_self(self) -> tp.Optional[BaseParserObject]:
        value = self.children["value"]
        if isinstance(value, ReferenceObject):
            value = value.absolute
        index = self.children["index"]
        if isinstance(index, ReferenceObject):
            index = index.absolute
        try:
            return value[index]
        except KeyError as error:
            logger.warning(f"{self.__class__.__name__} did not resolve: {repr(self)}\nKeyError: {error}")
        return None

    @cached_property
    def resolve_name(self) -> BaseParserObject:
        value = self.children["value"]
        if isinstance(value, ReferenceObject):
            value = value.resolve_name
        index = self.children["index"]
        if isinstance(index, ReferenceObject):
            index = index.resolve_name
        return self.resolve_self or Subscript(value, index)

    def __str__(self):
        return str(self.children["value"]) + "[" + str(self.children["index"]) + "]"

    def __repr__(self):
        return f"Subscript(value={repr(self.children['value'])}; index={repr(self.children['index'])})"

    @classmethod
    def from_ast(cls, node: ast.Subscript, **kwargs) -> 'Expression':
        value = Expression.from_ast(node.value)
        # todo: remove the right part when python3.8 support is dropped
        if isinstance(node.slice, ast.Slice) or is_instance(node.slice, "_ast.ExtSlice"):
            raise RuntimeError(f"Slices are not supported: {unparse(node)}")
        index = node.slice
        # todo: remove this when python3.8 support is dropped
        if is_instance(index, "_ast.Index"):
            index = index.value
        return cls(value, Expression.from_ast(index))


class Iterable(Expression):
    def __init__(self, iterable: tp.Iterable[Expression], iterable_type: str):
        Expression.__init__(self)
        self.type = iterable_type
        for index, value in enumerate(iterable):
            self.add_child(value, repr(Python.from_str(str(index))))

    def __getitem__(self, item: Python):
        return self.children[repr(item)]

    def __str__(self):
        if self.type == "list":
            lbr, rbr = "[", "]"
        elif self.type == "tuple":
            lbr, rbr = "(", ")"
        elif self.type == "set":
            lbr, rbr = "{", "}"
        else:
            raise RuntimeError(f"{self.type}")
        return lbr + ", ".join(map(str, self.children.values())) + rbr

    def __repr__(self):
        return f"Iterable:{self.type}(" + "; ".join(f"{k}: {repr(v)}" for k, v in self.children.items()) + ")"

    @classmethod
    def from_ast(cls, node: tp.Union[ast.Tuple, ast.List, ast.Set], **kwargs) -> 'Expression':
        result = []
        for item in node.elts:
            result.append(Expression.from_ast(item))
        if isinstance(node, ast.Tuple):
            iterable_type = "tuple"
        elif isinstance(node, ast.List):
            iterable_type = "list"
        elif isinstance(node, ast.Set):
            iterable_type = "set"
        else:
            raise TypeError(type(node))
        return cls(result, iterable_type)


class Call(Expression):
    def __init__(self, func: Expression, args: tp.List[Expression], keywords: tp.Dict[str, Expression]):
        Expression.__init__(self)
        self.add_child(func, "func")
        for index, arg in enumerate(args):
            self.add_child(arg, "arg_" + str(index))
        for key, value in keywords.items():
            self.add_child(value, "keyword_" + key)

    def __str__(self):
        return str(self.children["func"]) + "(" + \
               ", ".join(
                   [
                       str(self.children[arg]) for arg in self.children.keys() if arg.startswith("arg_")
                   ] + [
                       f"{remove_prefix(keyword, 'keyword_')}={str(self.children[keyword])}" for keyword in self.children.keys() if keyword.startswith("keyword_")
                   ]
               ) + ")"

    def __repr__(self):
        return f"Call({'; '.join([k + ' = ' + repr(v) for k, v in self.children.items()])})"

    @classmethod
    def from_ast(cls, node: ast.Call, **kwargs) -> 'Call':
        func = Expression.from_ast(node.func)
        args = []
        keywords = {}
        for arg in node.args:
            if isinstance(arg, ast.Starred):
                raise StarError(f"Starred calls are not supported: {unparse(node)}")
            args.append(Expression.from_ast(arg))
        for keyword in node.keywords:
            if keyword.arg is None:
                raise StarError(f"Starred calls are not supported: {unparse(node)}")
            keywords[str(keyword.arg)] = Expression.from_ast(keyword.value)
        return cls(func, args, keywords)
