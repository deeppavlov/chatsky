"""
Expressions
-----------
This module defines parser object classes that subclass from :py:class:`~.Expression`.
"""
from inspect import Signature, Parameter
import typing as tp
import ast
import logging
from enum import Enum

from dff.utils.parser.parser_objects.base_classes import BaseParserObject, Expression, ReferenceObject
from dff.utils.parser.exceptions import StarError
from dff.utils.parser.utils import is_instance, unparse, cached_property

if tp.TYPE_CHECKING:
    from dff.utils.parser.namespace import Namespace

logger = logging.getLogger(__name__)


class String(Expression):
    """
    This class is for nodes that represent :py:class:`ast.Str` (for python 3.7)
    or :py:class:`ast.Constant` with str value.
    """

    def __init__(self, string: str):
        super().__init__()
        self.string = string

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        return repr(self.string)

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.Str, ast.Constant], **kwargs) -> "String":  # type: ignore
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        if isinstance(node, ast.Str):  # todo: remove this when python3.7 support is dropped
            return cls(node.s)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return cls(node.value)
        return None


class Dict(Expression):
    """
    This class if for nodes that represent :py:class:`ast.Dict`.
    """

    def __init__(self, keys: tp.List[Expression], values: tp.List[Expression]):
        super().__init__()
        self.__keys: tp.List[tp.Tuple[Expression, str]] = []
        for key, value in zip(keys, values):
            self.__keys.append((key, str(key)))
            self.add_child(key, self._key(key))
            self.add_child(value, self._value(key))

    @staticmethod
    def _key(str_key: tp.Union[Expression, str]) -> str:
        """Get a name which is used to store a child that is a key in the dictionary.

        :param str_key: An object or a string representation of an object.
            The object represents a key in the dictionary.
        :return: Name of a child-key.
        """
        if not isinstance(str_key, str):
            str_key = str(str_key)
        return "key_" + str_key

    @staticmethod
    def _value(str_value: tp.Union[Expression, str]) -> str:
        """Get a name which is used to store a child that is a value in the dictionary.

        :param str_value: An object or a string representation of an object.
            The object represents a value in the dictionary.
        :return: Name of a child-value.
        """
        if not isinstance(str_value, str):
            str_value = str(str_value)
        return "value_" + str_value

    @staticmethod
    def _clear(child_name: str) -> str:
        """Get a string representation of a key that is associated with a child under the name `child_name`.

        :param child_name: A name of a child.
        :return: A string representation of the corresponding key.
        """
        if child_name.startswith("value_"):
            return child_name[len("value_") :]  # noqa: E203
        if child_name.startswith("key_"):
            return child_name[len("key_") :]  # noqa: E203
        return child_name

    def key_by_value(self, value: Expression) -> Expression:
        """Get a key by the value.

        :param value: Value stored in a dictionary.
        :return: A key that is associated with the value.
        """
        child_name = value._name
        if child_name is None:
            raise RuntimeError(f"Value does not have a parent: {value}")
        return self.children[self._key(self._clear(child_name))]

    def keys(self) -> tp.Iterator[Expression]:
        """An iterator over keys in the dictionary."""
        for _, key_str in self.__keys:
            yield self.children[self._key(key_str)]

    def values(self) -> tp.Iterator[Expression]:
        """An iterator over values in the dictionary."""
        for _, key_str in self.__keys:
            yield self.children[self._value(key_str)]

    def items(self) -> tp.Iterator[tp.Tuple[Expression, Expression]]:
        """An iterator over tuples of keys and values in the dictionary."""
        for _, key_str in self.__keys:
            yield self.children[self._key(key_str)], self.children[self._value(key_str)]

    @cached_property
    def _keys(self) -> tp.Dict[Expression, str]:
        """A mapping from dictionary keys to their string representations."""
        result = {}
        for key, value in self.__keys:
            result[key] = value
        return result

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        items = [
            (indent * " " if indent else "")
            + self.children[self._key(key)].dump(
                current_indent=0 if indent is None else (current_indent + indent), indent=indent
            )
            + ": "
            + self.children[self._value(key)].dump(
                current_indent=0 if indent is None else (current_indent + indent), indent=indent
            )
            + ","
            for _, key in self.__keys
        ]
        if indent is None:
            return "{" + " ".join(items) + "}"
        else:
            return ("\n" + current_indent * " ").join(["{", *items, "}"])

    def __getitem__(self, item: tp.Union[Expression, str]) -> Expression:
        """Get dictionary value based on a key.

        :param item: Either a key or a string representation of a key.
        :return: Dictionary value.
        :raises TypeError:
            If the type of `item` is not :py:class:`.BaseParserObject` nor `str`.
        :raises KeyError:
            If the key is not in the dictionary.
        """
        if isinstance(item, Expression):
            key = self._keys[item]
            return self.children[self._value(key)]
        elif isinstance(item, str):
            return self.children[self._value(item)]
        else:
            raise TypeError(f"Item {repr(item)} is not `BaseParserObject` nor `str`")

    def get(self, item: tp.Union[Expression, str], default=None) -> Expression:
        """Get dictionary value based on a key.

        :param item: Either a key or a string representation of a key.
        :param default: Value to return if the dictionary does not have the `item` key.
        :return: Dictionary value.
        :raises TypeError:
            If the type of `item` is not :py:class:`.BaseParserObject` nor `str`.
        """
        if isinstance(item, Expression):
            key = self._keys.get(item)
            if key is None:
                return default
            return self.children.get(self._value(key), default)
        elif isinstance(item, str):
            return self.children.get(self._value(item), default)
        else:
            raise TypeError(f"Item {repr(item)} is not `BaseParserObject` nor `str`")

    @classmethod
    @tp.overload
    def from_ast(cls, node: ast.Dict, **kwargs) -> "Dict":  # type: ignore
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        if not isinstance(node, ast.Dict):
            return None
        keys, values = [], []
        for key, value in zip(node.keys, node.values):
            if key is None:
                raise StarError(f"Dict unpacking is not supported: {unparse(node)}")
            keys.append(Expression.auto(key))
            values.append(Expression.auto(value))
        return cls(keys, values)


class Name(Expression, ReferenceObject):
    """
    This class if for nodes that represent :py:class:`ast.Name`.
    """

    def __init__(self, name: str):
        Expression.__init__(self)
        ReferenceObject.__init__(self)
        self.name = name

    @cached_property
    def _resolve_once(self) -> tp.Optional[BaseParserObject]:
        result = self.namespace.get_object(self.name)
        if result is None:
            logger.debug(
                f"{self.__class__.__name__} did not resolve: {str(self)}\n"
                f"Object {self.name} not found in {self.namespace}"
            )
        return result

    @cached_property
    def referenced_object(self) -> str:
        resolved = self._resolve_once
        if isinstance(resolved, ReferenceObject):
            return resolved.referenced_object
        return ".".join([*self.namespace.location, self.name])

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        return self.name

    @classmethod
    @tp.overload
    def from_ast(cls, node: ast.Name, **kwargs) -> "Name":  # type: ignore
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        if not isinstance(node, ast.Name):
            return None
        return cls(node.id)


class Attribute(Expression, ReferenceObject):
    """
    This class if for nodes that represent :py:class:`ast.Attribute`.
    """

    def __init__(self, value: Expression, attr: str):
        Expression.__init__(self)
        ReferenceObject.__init__(self)
        self.add_child(value, "value")
        self.attr = attr

    @cached_property
    def _resolve_once(self) -> tp.Optional[BaseParserObject]:
        value: tp.Optional[tp.Union[BaseParserObject, "Namespace"]] = ReferenceObject.resolve_absolute(
            self.children["value"]
        )
        if is_instance(value, "dff.utils.parser.namespace.Namespace"):
            value = tp.cast("Namespace", value)
            obj = value.get_object(self.attr)
            if obj is None:
                logger.debug(
                    f"{self.__class__.__name__} did not resolve: {str(self)}\nKey {self.attr} does not exist in {value}"
                )
            return obj
        return None

    @cached_property
    def referenced_object(self) -> str:
        resolved = self._resolve_once
        if isinstance(resolved, ReferenceObject):
            return resolved.referenced_object
        value = self.children["value"]
        return value.true_value() + "." + self.attr

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        return self.children["value"].dump(current_indent, indent) + "." + self.attr

    @classmethod
    @tp.overload
    def from_ast(cls, node: ast.Attribute, **kwargs) -> "Attribute":  # type: ignore
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        if not isinstance(node, ast.Attribute):
            return None
        return cls(Expression.auto(node.value), node.attr)


class Subscript(Expression, ReferenceObject):
    """
    This class if for nodes that represent :py:class:`ast.Subscript`.
    """

    def __init__(self, value: Expression, index: Expression):
        Expression.__init__(self)
        ReferenceObject.__init__(self)
        self.add_child(value, "value")
        self.add_child(index, "index")

    @cached_property
    def _resolve_once(self) -> tp.Optional[BaseParserObject]:
        value: tp.Optional[BaseParserObject] = ReferenceObject.resolve_absolute(self.children["value"])
        index: tp.Optional[BaseParserObject] = ReferenceObject.resolve_absolute(self.children["index"])

        debug_message = f"{self.__class__.__name__} did not resolve: {str(self)}"

        if value is None:
            logger.debug(f"{debug_message}\nValue did not resolve: {self.children['value']}")
            return None
        if index is None:
            logger.debug(f"{debug_message}\nIndex did not resolve: {self.children['index']}")
            return None
        if not isinstance(value, (Dict, Iterable)):
            logger.debug(f"{debug_message}\nValue is not a `Dict`: {value}")
            return None
        if not isinstance(index, Expression):
            logger.debug(f"{debug_message}\nIndex is not an `Expression`: {index}")
            return None
        result = value.get(index)
        if result is None:
            logger.debug(f"{debug_message}\nKey not found.\nKey: {index}\nDict: {value}")
            return None
        return result

    @cached_property
    def referenced_object(self) -> str:
        resolved = self._resolve_once
        if isinstance(resolved, ReferenceObject):
            return resolved.referenced_object
        value = self.children["value"]
        index = self.children["index"]
        return value.true_value() + "[" + index.true_value() + "]"

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        return (
            self.children["value"].dump(current_indent, indent)
            + "["
            + self.children["index"].dump(current_indent, indent)
            + "]"
        )

    @classmethod
    @tp.overload
    def from_ast(cls, node: ast.Subscript, **kwargs) -> "Subscript":  # type: ignore
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        if not isinstance(node, ast.Subscript):
            return None
        value = Expression.auto(node.value)
        # todo: remove the right part when python3.8 support is dropped
        if isinstance(node.slice, ast.Slice) or is_instance(node.slice, "_ast.ExtSlice"):
            raise RuntimeError(f"Slices are not supported: {unparse(node)}")
        index = node.slice
        # todo: remove this when python3.8 support is dropped
        if is_instance(index, "_ast.Index"):
            index = index.value  # type: ignore
        return cls(value, Expression.auto(index))


class Iterable(Expression):
    """
    This class if for nodes that represent :py:class:`ast.Tuple`, :py:class:`ast.List` or :py:class:`ast.Set`.
    """

    class Type(tuple, Enum):
        LIST = ("[", "]")
        TUPLE = ("(", ")")
        SET = ("{", "}")

    def __init__(self, iterable: tp.Iterable[Expression], iterable_type: Type):
        Expression.__init__(self)
        self.children: tp.Dict[str, Expression]
        self.type: Iterable.Type = iterable_type
        """Type of the iterable"""
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

    def get(self, item: tp.Union[Expression, str, int], default=None) -> Expression:
        if isinstance(item, str):
            return self.children.get(item, default)
        elif isinstance(item, int):
            return self.children.get(str(item), default)
        else:
            return self.children.get(str(item), default)

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        return (
            self.type.value[0]
            + ", ".join([child.dump(current_indent, indent) for child in self.children.values()])
            + ("," if (len(self.children) == 1 and self.type == Iterable.Type.TUPLE) else "")
            + self.type.value[1]
        )

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.Tuple, ast.List, ast.Set], **kwargs) -> "Iterable":  # type: ignore
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        if not isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return None
        result = []
        for item in node.elts:
            result.append(Expression.auto(item))
        if isinstance(node, ast.Tuple):
            iterable_type = Iterable.Type.TUPLE
        elif isinstance(node, ast.List):
            iterable_type = Iterable.Type.LIST
        else:
            iterable_type = Iterable.Type.SET
        return cls(result, iterable_type)


class Call(Expression):
    """
    This class if for nodes that represent :py:class:`ast.Call`.
    """

    def __init__(self, func: Expression, args: tp.List[Expression], keywords: tp.Dict[str, Expression]):
        Expression.__init__(self)
        self.add_child(func, "func")
        self.args: tp.List[Expression] = args
        self.keywords: tp.Dict[str, Expression] = keywords
        for index, arg in enumerate(args):
            self.add_child(arg, "arg_" + str(index))
        for key, value in keywords.items():
            self.add_child(value, "keyword_" + key)

    def get_args(self, func_sig: Signature) -> tp.Dict[str, Expression]:
        """
        Return a dictionary of pairs `{arg_name: arg_value}`.
        If `arg_name` corresponds to a collection of unbound arguments (such as `args` in `def func(*args, **kwargs):`),
        `arg_value` has type :py:class:`~.Iterable` (for a tuple of positional unbound arguments)
        or :py:class:`~.Dict`(for a dict of unbound keyword arguments).
        Note: alternative names for collections of unbound arguments are supported
        (i.e. if a function is defined as `def func(*func_args, **func_kwargs):`).

        :param func_sig: Function signature.
        :return: A mapping from argument names to their values (represented by :py:class:`.Expression`).
        :raises TypeError:
            If `self.args` and `self.kwargs` do not match function signature.
        """
        first_arg = list(func_sig.parameters.keys())[0]
        if first_arg in ("self", "cls"):
            stub = [None]
        else:
            stub = []

        params = func_sig.bind(*stub, *self.args, **self.keywords)
        params.apply_defaults()

        result: tp.Dict[str, Expression] = {}
        for key, value in params.arguments.items():
            if key not in ("self", "cls"):
                if func_sig.parameters[key].kind == Parameter.VAR_POSITIONAL:  # *args processing
                    result[key] = Iterable(value, Iterable.Type.TUPLE)
                elif func_sig.parameters[key].kind == Parameter.VAR_KEYWORD:  # **kwargs processing
                    result[key] = Dict(list(map(Expression.from_obj, value.keys())), list(value.values()))
                else:
                    result[key] = value if isinstance(value, Expression) else Expression.from_obj(value)
        return result

    @cached_property
    def func_name(self) -> str:
        """Name of the function being called. If function being called is a lambda function, it's body is returned."""
        func = self.children["func"]
        if isinstance(func, ReferenceObject):
            return func.referenced_object
        return str(func)

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        return (
            self.children["func"].dump(current_indent, indent)
            + "("
            + ", ".join(
                [
                    self.children[arg].dump(current_indent, indent)
                    for arg in self.children.keys()
                    if arg.startswith("arg_")
                ]
                + [
                    f"{keyword[len('keyword_'):]}={self.children[keyword].dump(current_indent, indent)}"
                    for keyword in self.children.keys()
                    if keyword.startswith("keyword_")
                ]
            )
            + ")"
        )

    @classmethod
    @tp.overload
    def from_ast(cls, node: ast.Call, **kwargs) -> "Call":  # type: ignore
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        if not isinstance(node, ast.Call):
            return None
        func = Expression.auto(node.func)
        args = []
        keywords = {}
        for arg in node.args:
            if isinstance(arg, ast.Starred):
                raise StarError(f"Starred calls are not supported: {unparse(node)}")
            args.append(Expression.auto(arg))
        for keyword in node.keywords:
            if keyword.arg is None:
                raise StarError(f"Starred calls are not supported: {unparse(node)}")
            keywords[str(keyword.arg)] = Expression.auto(keyword.value)
        return cls(func, args, keywords)


class Generator(BaseParserObject):
    """
    This class if for nodes that represent :py:class:`ast.comprehension`.
    """

    def __init__(self, target: Expression, iterator: Expression, ifs: tp.List[Expression], is_async: bool):
        BaseParserObject.__init__(self)
        self.add_child(target, "target")
        self.add_child(iterator, "iter")
        for index, if_expr in enumerate(ifs):
            self.add_child(if_expr, "if_" + str(index))
        self.is_async = is_async

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        ifs = [
            f"if {expression.dump(current_indent, indent)}"
            for key, expression in self.children.items()
            if key.startswith("if_")
        ]
        return (
            ("async " if self.is_async else "")
            + f"for {self.children['target'].dump(current_indent, indent)}"
            + f" in {self.children['iter'].dump(current_indent, indent)}"
            + (" " if ifs else "")
            + " ".join(ifs)
        )

    @classmethod
    @tp.overload
    def from_ast(cls, node: ast.comprehension, **kwargs) -> "Generator":  # type: ignore
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        if not isinstance(node, ast.comprehension):
            return None
        return cls(
            target=Expression.auto(node.target),
            iterator=Expression.auto(node.iter),
            ifs=[Expression.auto(if_expr) for if_expr in node.ifs],
            is_async=node.is_async == 1,
        )


class Comprehension(Expression):
    """
    This class if for nodes that represent :py:class:`ast.DictComp`, :py:class:`ast.ListComp`,
    :py:class:`ast.SetComp` or :py:class:`ast.GeneratorExp`.
    """

    class Type(tuple, Enum):
        LIST = ("[", "]")
        GEN = ("(", ")")
        SET = ("{", "}")
        DICT = (None, None)

    def __init__(
        self,
        element: tp.Union[Expression, tp.Tuple[Expression, Expression]],
        generators: tp.List[Generator],
        comp_type: Type,
    ):
        Expression.__init__(self)
        if isinstance(element, tuple):
            if comp_type is not Comprehension.Type.DICT:
                raise RuntimeError(comp_type)
            self.add_child(element[0], "key")
            self.add_child(element[1], "value")
        else:
            if comp_type is Comprehension.Type.DICT:
                raise RuntimeError(comp_type)
            self.add_child(element, "element")

        self.comp_type: Comprehension.Type = comp_type
        """Type of comprehension"""
        for index, generator in enumerate(generators):
            self.add_child(generator, "gens_" + str(index))

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        gens = [gen.dump(current_indent, indent) for key, gen in self.children.items() if key.startswith("gens_")]
        if self.comp_type is Comprehension.Type.DICT:
            return (
                f"{{{self.children['key'].dump(current_indent, indent)}: "
                f"{self.children['value'].dump(current_indent, indent)}" + (" " if gens else "") + " ".join(gens) + "}"
            )
        else:
            return (
                self.comp_type.value[0]
                + self.children["element"].dump(current_indent, indent)
                + (" " if gens else "")
                + " ".join(gens)
                + self.comp_type.value[1]
            )

    @classmethod
    @tp.overload
    def from_ast(  # type: ignore
        cls, node: tp.Union[ast.ListComp, ast.SetComp, ast.GeneratorExp], **kwargs
    ) -> "Comprehension":
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        if not isinstance(node, (ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            return None
        gens = [Generator.from_ast(gen) for gen in node.generators]
        if isinstance(node, ast.DictComp):
            return cls(
                (Expression.auto(node.key), Expression.auto(node.value)),
                gens,
                Comprehension.Type.DICT,
            )
        elif isinstance(node, ast.ListComp):
            comp_type = Comprehension.Type.LIST
        elif isinstance(node, ast.SetComp):
            comp_type = Comprehension.Type.SET
        elif isinstance(node, ast.GeneratorExp):
            comp_type = Comprehension.Type.GEN
        return cls(
            Expression.auto(node.elt),
            gens,
            comp_type,
        )
