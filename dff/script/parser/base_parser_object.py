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
    try:
        from cached_property import cached_property  # todo: remove this when python3.7 support is dropped
    except ImportError:
        raise ImportError(f"Module `cached_property` is not installed. Install it with `pip install dff[parser]`.")

try:
    from ast import unparse
except ImportError:
    try:
        from astunparse import unparse  # todo: remove this when python3.8 support is dropped
    except ImportError:
        raise ImportError(f"Module `astunparse` is not installed. Install it with `pip install dff[parser]`.")

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
    def resolve(self) -> 'BaseParserObject':
        if isinstance(self, ReferenceObject):
            return self.absolute or self
        return self

    @cached_property
    def names(self) -> tp.Set[str]:
        result = set()
        if isinstance(self, Name):
            result.add(self.name)
        for child in self.children.values():
            result.update(child.names)
        return result

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

    @abstractmethod
    def dump(self, current_indent=0, indent=4) -> str:
        ...  # todo: replace str in all dump defs with dump calls

    def __repr__(self) -> str:
        return self.__class__.__name__ + "(" + self.dump() + ")"

    def __str__(self) -> str:
        return self.dump()

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
    def from_ast(cls, node, **kwargs) -> tp.Union[tp.Dict[str, 'Statement'], 'Python']:
        if isinstance(node, ast.Import):
            return Import.from_ast(node)
        if isinstance(node, ast.ImportFrom):
            return ImportFrom.from_ast(node)
        if isinstance(node, ast.Assign):
            return Assignment.from_ast(node)
        if isinstance(node, ast.AnnAssign):
            if node.value is not None:
                return Assignment.from_ast(node)
        return Python.from_ast(node)


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
        if isinstance(node, (ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            return Comprehension.from_ast(node)
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
    def resolve_name(self) -> tp.Optional[BaseParserObject]:
        """
        Same as `absolute` but instead of returning None at failed resolution returns the name of the absolute object
        """
        ...

    def __hash__(self):
        return BaseParserObject.__hash__(self.resolve_name or self)

    def __eq__(self, other):
        if isinstance(other, ReferenceObject):
            return BaseParserObject.__eq__(self.resolve_name or self, other.resolve_name or self)
        return BaseParserObject.__eq__(self.resolve_name or self, other)


def module_name_to_expr(module_name: tp.List[str]) -> tp.Union['Name', 'Attribute']:
    """Convert a module name in the form of a dot-separated string to an instance of Attribute or Name

    :param module_name: a list of strings that represent a module or its objects
    :type module_name: list[str]
    :return: An instance of an object that would represent `module_name`
    :rtype: :py:class:`.Name` | :py:class:`.Attribute`
    """
    if len(module_name) == 0:
        raise RuntimeError("Empty name")
    result = Name(module_name[0])
    for attr in module_name[1:]:
        result = Attribute(result, attr)
    return result


class Import(Statement, ReferenceObject):
    def __init__(self, module: str, alias: tp.Optional[str] = None):
        Statement.__init__(self)
        ReferenceObject.__init__(self)
        self.module = module
        self.alias = alias

    def dump(self, current_indent=0, indent=4) -> str:
        return f"import {self.module}" + (f" as {self.alias}" if self.alias else "")

    @cached_property
    def resolve_self(self) -> tp.Optional[BaseParserObject]:
        try:
            return self.dff_project[".".join(self.namespace.resolve_relative_import(self.module))]
        except KeyError as error:
            logger.debug(f"{self.__class__.__name__} did not resolve: {repr(self)}\nKeyError: {error}")
            return None

    @cached_property
    def resolve_name(self) -> tp.Optional[BaseParserObject]:
        return self.absolute or module_name_to_expr(self.module.split("."))

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

    def dump(self, current_indent=0, indent=4) -> str:
        return f"from {self.level * '.' + self.module} import {self.obj}" + (f" as {self.alias}" if self.alias else "")

    @cached_property
    def resolve_self(self) -> tp.Optional[BaseParserObject]:
        try:
            return self.dff_project[self.namespace.resolve_relative_import(self.module, self.level)][self.obj]  # todo: perf: use get instead
        except KeyError as error:
            logger.debug(f"{self.__class__.__name__} did not resolve: {repr(self)}\nKeyError: {error}")
            return None

    @cached_property
    def resolve_name(self) -> tp.Optional[BaseParserObject]:
        resolved = self.resolve_self
        if isinstance(resolved, ReferenceObject):
            resolved = resolved.resolve_name
        if self.level > 0:
            substitute_module_name = self.namespace.resolve_relative_import(self.module, self.level) + [self.obj]
        else:
            substitute_module_name = self.module.split(".") + [self.obj]
        return resolved or module_name_to_expr(substitute_module_name)

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

    def dump(self, current_indent=0, indent=4) -> str:
        return f"{str(self.children['target'])} = {str(self.children['value'])}"

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

    def dump(self, current_indent=0, indent=4) -> str:
        return repr(self.string)

    @classmethod
    def from_ast(cls, node: tp.Union['ast.Str', ast.Constant], **kwargs) -> 'String':
        if is_instance(node, "_ast.Str"):  # todo: remove this when python3.7 support is dropped
            return cls(node.s)
        elif isinstance(node, ast.Constant):
            return cls(node.value)
        raise RuntimeError(f"Node {node} is not str")


class Python(Expression, Statement):
    def __init__(self, node: ast.AST):
        super().__init__()
        for key, value in node.__dict__.items():
            if isinstance(value, ast.expr):
                self.add_child(Expression.from_ast(value), key)
            elif isinstance(value, Iterable):
                for index, child in enumerate(value):
                    if isinstance(child, ast.expr):
                        self.add_child(Expression.from_ast(child), key + "_" + str(index))
        self.string = remove_suffix(unparse(node), "\n")
        self.type = node.__class__.__name__

    def dump(self, current_indent=0, indent=4) -> str:
        return self.string

    @classmethod
    def from_str(cls, string: str) -> 'Python':  # todo: add support for statements
        return cls(ast.parse(string).body[0].value)

    @classmethod
    def from_ast(cls, node: ast.AST, **kwargs) -> 'Python':
        return cls(node)


class Dict(Expression):
    def __init__(self, keys: tp.List[Expression], values: tp.List[Expression]):
        super().__init__()
        self.__keys: tp.List[tp.Tuple[Expression, str]] = []
        for key, value in zip(keys, values):
            self.__keys.append((key, str(key)))
            self.add_child(key, self._key(key))
            self.add_child(value, self._value(key))

    @staticmethod
    def _key(str_key) -> str:
        if not isinstance(str_key, str):
            str_key = str(str_key)
        return "key_" + str_key

    @staticmethod
    def _value(str_value) -> str:
        if not isinstance(str_value, str):
            str_value = str(str_value)
        return "value_" + str_value

    @staticmethod
    def _clear(string: str) -> str:
        if string.startswith("value_"):
            return string[len("value_"):]
        if string.startswith("key_"):
            return string[len("key_"):]
        return string

    def key_by_value(self, value: Expression) -> Expression:
        return self.children[self._key(self._clear(value.append_path))]

    def keys(self) -> tp.Iterator[Expression]:
        for _, key_str in self.__keys:
            yield self.children[self._key(key_str)]

    def values(self) -> tp.Iterator[Expression]:
        for _, key_str in self.__keys:
            yield self.children[self._value(key_str)]

    def items(self) -> tp.Iterator[tp.Tuple[Expression, Expression]]:
        for _, key_str in self.__keys:
            yield self.children[self._key(key_str)], self.children[self._value(key_str)]

    @cached_property
    def _keys(self) -> tp.Dict[Expression, str]:
        result = {}
        for key, value in self.__keys:
            result[key] = value
        return result

    def dump(self, current_indent=0, indent=4) -> str:
        return "{\n" + "".join(
            [(current_indent + indent) * " " + f"{self.children[self._key(key)].dump(current_indent=(current_indent + indent))}: {self.children[self._value(key)].dump(current_indent=(current_indent + indent))},\n" for _, key in self.__keys]
        ) + current_indent * " " + "}"

    def __getitem__(self, item: tp.Union[Expression, str]):
        if isinstance(item, Expression):
            key = self._keys[item]
            return self.children[self._value(key)]
        elif isinstance(item, str):
            return self.children[self._value(item)]
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
        return cls(keys, values)


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
            logger.debug(f"{self.__class__.__name__} did not resolve: {repr(self)}\nKeyError: {error}")
            return None

    @cached_property
    def resolve_name(self) -> tp.Optional[BaseParserObject]:
        resolved = self.resolve_self
        if isinstance(resolved, ReferenceObject):
            return resolved.resolve_name
        return resolved or self

    def dump(self, current_indent=0, indent=4) -> str:
        return self.name

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
            logger.debug(f"{self.__class__.__name__} did not resolve: {repr(self)}\nKeyError: {error}")
        return None

    @cached_property
    def resolve_name(self) -> tp.Optional[BaseParserObject]:
        value = self.children["value"]
        if isinstance(value, ReferenceObject):
            value = value.resolve_name
        return self.resolve_self or Attribute(value, self.attr)

    def dump(self, current_indent=0, indent=4) -> str:
        return str(self.children["value"]) + "." + self.attr

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
            logger.debug(f"{self.__class__.__name__} did not resolve: {repr(self)}\nKeyError: {error}")
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

    def dump(self, current_indent=0, indent=4) -> str:
        return str(self.children["value"]) + "[" + str(self.children["index"]) + "]"

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
        self.children: tp.Dict[str, Expression]
        self.type = iterable_type
        for index, value in enumerate(iterable):
            self.add_child(value, str(index))

    def __iter__(self):
        yield from self.children.values()

    def __len__(self):
        return len(self.children)

    def __getitem__(self, item: tp.Union[Expression, str, int]) -> Expression:
        if isinstance(item, str):
            return self.children[item]
        elif isinstance(item, int):
            return self.children[str(item)]
        else:
            return self.children[str(item)]

    def dump(self, current_indent=0, indent=4) -> str:
        if self.type == "list":
            lbr, rbr = "[", "]"
        elif self.type == "tuple":
            lbr, rbr = "(", ")"
        elif self.type == "set":
            lbr, rbr = "{", "}"
        else:
            raise RuntimeError(f"{self.type}")
        return lbr + ", ".join(map(str, self.children.values())) + rbr

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

    def get_args(self, seq_arg_list: tp.List[str]) -> dict:
        args = {}
        for index, arg in enumerate(seq_arg_list):
            args[arg] = self.children.get("arg_" + str(index)) or self.children.get("keyword_" + arg)
        return args

    @cached_property
    def func_name(self) -> str:
        if isinstance(self.children["func"], ReferenceObject):
            return str(self.children["func"].resolve_name)
        return str(self.children["func"])

    def dump(self, current_indent=0, indent=4) -> str:
        return str(self.children["func"]) + "(" + \
               ", ".join(
                   [
                       str(self.children[arg]) for arg in self.children.keys() if arg.startswith("arg_")
                   ] + [
                       f"{remove_prefix(keyword, 'keyword_')}={str(self.children[keyword])}" for keyword in self.children.keys() if keyword.startswith("keyword_")
                   ]
               ) + ")"

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


class Generator(BaseParserObject):
    def __init__(self, target: Expression, iterator: Expression, ifs: tp.List[Expression], is_async: bool):
        BaseParserObject.__init__(self)
        self.add_child(target, "target")
        self.generated_names = target.names
        self.add_child(iterator, "iter")
        for index, if_expr in enumerate(ifs):
            self.add_child(if_expr, "if_" + str(index))
        self.is_async = is_async

    def dump(self, current_indent=0, indent=4) -> str:
        ifs = [f"if {str(expr)}" for key, expr in self.children.items() if key.startswith("if_")]
        return ("async " if self.is_async else "") + f"for {self.children['target']} in {self.children['iter']}" + (" " if ifs else "") + " ".join(ifs)

    @classmethod
    def from_ast(cls, node: ast.comprehension, **kwargs):
        if not isinstance(node, ast.comprehension):
            raise TypeError(type(node))
        return cls(
            target=Expression.from_ast(node.target),
            iterator=Expression.from_ast(node.iter),
            ifs=[Expression.from_ast(if_expr) for if_expr in node.ifs],
            is_async=node.is_async == 1,
        )


class Comprehension(Expression):
    def __init__(
        self,
        element: tp.Union[Expression, tp.Tuple[Expression, Expression]],
        generators: tp.List[Generator],
        comp_type: tp.Optional[str]
    ):
        Expression.__init__(self)
        if isinstance(element, tuple):
            if not comp_type == "dict":
                raise RuntimeError(comp_type)
            self.add_child(element[0], "key")
            self.add_child(element[1], "value")
        else:
            if comp_type == "dict":
                raise RuntimeError(comp_type)
            self.add_child(element, "element")

        self.comp_type = comp_type
        self.generated_names = set()
        for index, generator in enumerate(generators):
            self.add_child(generator, "gens_" + str(index))
            self.generated_names.update(generator.generated_names)

    @cached_property
    def names(self) -> tp.Set[str]:
        if cached_property.__module__ == "cached_property":
            get = (self, BaseParserObject)
        else:
            get = (self,)
        return BaseParserObject.names.__get__(*get).difference(self.generated_names)

    def dump(self, current_indent=0, indent=4) -> str:
        gens = [str(gen) for key, gen in self.children.items() if key.startswith("gens_")]
        if self.comp_type == "dict":
            return f"{{{str(self.children['key'])}: {str(self.children['value'])}" + (" " if gens else "") + " ".join(gens) + "}"
        else:
            if self.comp_type == "list":
                l_br, r_br = "[", "]"
            elif self.comp_type == "set":
                l_br, r_br = "{", "}"
            elif self.comp_type == "gen":
                l_br, r_br = "(", ")"
            else:
                raise RuntimeError(self.comp_type)
            return l_br + str(self.children["element"]) + (" " if gens else "") + " ".join(gens) + r_br

    @classmethod
    def from_ast(cls, node: tp.Union[ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp], **kwargs) -> 'Expression':
        gens = [Generator.from_ast(gen) for gen in node.generators]
        if isinstance(node, ast.DictComp):
            return cls(
                (Expression.from_ast(node.key), Expression.from_ast(node.value)),
                gens,
                "dict",
            )
        if isinstance(node, ast.ListComp):
            comp_type = "list"
        elif isinstance(node, ast.SetComp):
            comp_type = "set"
        elif isinstance(node, ast.GeneratorExp):
            comp_type = "gen"
        else:
            raise TypeError(type(node))
        return cls(
            Expression.from_ast(node.elt),
            gens,
            comp_type,
        )

