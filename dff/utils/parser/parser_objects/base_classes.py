"""
Base Parser Object
------------------
This module defines base classes for all the parser objects.

This module also defines a Python class which is used when an `ast` node is not represented by any class
defined in this package.
"""
import typing as tp
from abc import ABC, abstractmethod
from collections import defaultdict
import ast

if tp.TYPE_CHECKING:
    from dff.utils.parser.namespace import Namespace
    from dff.utils.parser.dff_project import DFFProject
from dff.utils.parser.exceptions import ParsingError
from dff.utils.parser.utils import cached_property, unparse


class BaseParserObject(ABC):
    """
    An interface for other parser objects specifying methods that all parser objects should define:
        - :py:meth:`~.BaseParserObject.dump`
        - :py:meth:`~.BaseParserObject.from_ast`

    This class also implements some useful methods for any parser object.
    """

    def __init__(self):
        self.parent: tp.Optional[BaseParserObject] = None
        "Parent node."
        self._name: tp.Optional[str] = None
        "Name of the node: `path = parent.path + _name`."
        self.children: tp.MutableMapping[str, BaseParserObject] = {}
        "Mapping from child names to child nodes."

    def dependencies(self) -> tp.Dict[str, tp.Set[str]]:
        """A list of objects defined in :py:class:`.Namespace`\\s that are used inside current node.

        :return: A mapping from :py:class:`.Namespace`\\s names to sets of object names.
        """
        result: tp.DefaultDict[str, tp.Set[str]] = defaultdict(set)
        if len(self.path) >= 2:
            result[self.path[0]].add(self.path[1])
        else:  # self is a Namespace, return no dependencies
            return result

        if isinstance(self, ReferenceObject):
            resolved = self._resolve_once
            if resolved is not None:
                for namespace, objects in resolved.dependencies().items():
                    result[namespace].update(objects)

        for child in self.children.values():
            for namespace, objects in child.dependencies().items():
                result[namespace].update(objects)
        return dict(result)

    def add_child(self, child: "BaseParserObject", asname: str):
        """Add a child node `child` by the name `asname`.

        :param child: Child node to add.
        :param asname: Name of the child node.
        """
        child.parent = self
        child._name = asname
        self.children[asname] = child

    def resolve_path(self, path: tp.Tuple[str, ...]) -> "BaseParserObject":
        """Resolve tree path relative to this node.

        :param path: A tuple of child names.
        :raises KeyError:
            If a key in `path` cannot be found in children.
        :return: A child path[-1] of a child path[-2] of .. a child path[0] of this object.
        """
        if len(path) == 0:
            return self
        child = self.children.get(path[0])
        if child is None:
            raise KeyError(f"Not found key {path[0]} in {str(self)}")
        return child.resolve_path(path[1:])

    @cached_property
    def path(self) -> tp.Tuple[str, ...]:
        """Path to this node from the tree root node."""
        if self._name is None:
            raise RuntimeError(f"Name is not set: {str(self)}")
        if self.parent is None:
            raise RuntimeError(f"Parent is not set: {str(self)}")
        return self.parent.path + (self._name,)

    @cached_property
    def namespace(self) -> "Namespace":
        """Namespace this object belongs to."""
        if self.parent is None:
            raise RuntimeError(f"Parent is not set: {str(self)}")
        return self.parent.namespace

    @cached_property
    def dff_project(self) -> "DFFProject":
        """DFFProject this object belongs to."""
        return self.namespace.dff_project

    @abstractmethod
    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        """
        Dump object as string. `current_indent` should already be applied to the current line by the node's parent.
        `current_indent` is supposed to be used only when creating new lines.

        :param current_indent: Current indentation level (in whitespace number), defaults to 0.
        :param indent:
            Indentation increment (in whitespace number), defaults to 4.
            If set to None, an object is dumped in one line.
        :return: Representation of the object as a string.
        """
        raise NotImplementedError()

    def __repr__(self) -> str:
        return self.__class__.__name__ + "(" + self.true_value() + ")"

    def __str__(self) -> str:
        return self.dump()

    def true_value(self) -> str:
        """Return the true value of the object that is used to compare objects and compute hash."""
        return self.dump(indent=None)

    def __hash__(self):
        return hash(self.true_value())

    def __eq__(self, other):
        if isinstance(other, BaseParserObject):
            return self.true_value() == other.true_value()
        if isinstance(other, str):
            return self.true_value() == other
        return NotImplemented

    @classmethod
    @abstractmethod
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs):
        """Construct an object from an :py:class:`ast.stmt` or :py:class:`ast.expr`.

        :param node: AST node to construct the object from.
        :return: Constructed object(s) or None if an object cannot be constructed from `node`.
        """
        raise NotImplementedError()


class Statement(BaseParserObject, ABC):
    """
    This class is for nodes that represent :py:class:`ast.stmt`.
    """

    def __init__(self):
        BaseParserObject.__init__(self)
        self.parent: tp.Optional[Namespace] = None
        self.children: tp.MutableMapping[str, Expression] = {}

    @classmethod
    @abstractmethod
    def from_ast(
        cls, node: tp.Union[ast.stmt, ast.expr], **kwargs
    ) -> tp.Optional[tp.Union[tp.Mapping[str, "Statement"], "Python"]]:
        """
        Extract statements from ast node.

        :return:
            - None, if type of the `node` is not compatible with the current class.
            - For non-:py:class:`~.Python` classes
              return a mapping from names of defined objects inside the statement to their definitions.
            - :py:class:`~.Python` should return an instance of itself.
        """
        raise NotImplementedError()

    @classmethod
    @tp.overload
    def auto(cls, node: ast.stmt, **kwargs) -> tp.Union[tp.Mapping[str, "Statement"], "Python"]:  # type: ignore
        ...

    @classmethod
    @tp.overload
    def auto(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def auto(cls, node, **kwargs):
        """Construct a statement automatically choosing the correct type."""
        if not isinstance(node, ast.stmt):
            return None
        for _cls in Statement.__subclasses__():
            if _cls != Python:
                obj = _cls.from_ast(node, **kwargs)
                if obj is not None:
                    return obj
        return Python.from_ast(node, **kwargs)


class Expression(BaseParserObject, ABC):
    """
    This class is for nodes that represent :py:class:`ast.expr`.
    """

    def __init__(self):
        BaseParserObject.__init__(self)
        self.parent: tp.Optional[tp.Union[Statement, Expression]] = None
        self.children: tp.MutableMapping[str, Expression] = {}

    @classmethod
    @abstractmethod
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> tp.Optional["Expression"]:
        raise NotImplementedError()

    @classmethod
    def from_str(cls, string: str) -> "Expression":
        """
        Construct an expression from a string representing it.

        :raises ParsingError:
            - If a string represents anything but a single expression (:py:class:`ast.Expr`).
        """
        body = ast.parse(string).body
        if len(body) != 1:
            raise ParsingError(f"Body should contain only one expression: {string}")
        statement = body[0]
        if not isinstance(statement, ast.Expr):
            raise ParsingError(f"Body should contain only expressions: {string}")
        return cls.auto(statement.value)

    @classmethod
    def from_obj(cls, obj: object) -> "Expression":
        """Construct an expression representing an object."""
        return cls.from_str(repr(obj))

    @classmethod
    @tp.overload
    def auto(cls, node: ast.expr, **kwargs) -> "Expression":  # type: ignore
        ...

    @classmethod
    @tp.overload
    def auto(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def auto(cls, node, **kwargs):
        """Construct an expression automatically choosing the correct type."""
        if not isinstance(node, ast.expr):
            return None
        for _cls in Expression.__subclasses__():
            if _cls != Python:
                obj = _cls.from_ast(node, **kwargs)
                if obj is not None:
                    return obj
        return Python.from_ast(node, **kwargs)


class ReferenceObject(BaseParserObject, ABC):
    """
    An interface for reference objects. Reference objects are objects that reference other objects,
    e.g. Name, Import, Subscript.
    """

    def __init__(self):
        BaseParserObject.__init__(self)

    @cached_property
    @abstractmethod
    def _resolve_once(self) -> tp.Optional[BaseParserObject]:
        """Try to find the object being referenced by the object.

        :return: Referenced object or None if it can't be resolved.
        """
        raise NotImplementedError()

    @cached_property
    def absolute(self) -> tp.Optional[BaseParserObject]:  # todo: handle recursion
        """An absolute object -- if the current object is a reference to another reference, that reference will
        be resolved as well.

        :return: A final object that is not :py:class:`.ReferenceObject` or None if any object cannot be resolved.
        """
        resolved = self._resolve_once
        if isinstance(resolved, ReferenceObject):
            return resolved.absolute
        return resolved

    @cached_property
    @abstractmethod
    def referenced_object(self) -> str:
        """
        Return a path of a referenced object (as well as modifiers such as indexes or attribute references).

        So if `ReferenceObject` is `from dff import pipeline as pl referenced_object` for `pl` is `dff.pipeline`.
        However, if `ReferencedObject` is `pl.Pipeline` or `pl.dictionary[pl.number][5]` then their
        `referenced_object`\\s are, respectively, `dff.pipeline.Pipeline` and
        `dff.pipeline.dictionary[dff.pipeline.number][5]`.
        """
        raise NotImplementedError()

    def __repr__(self):
        if self.dump(indent=None) == self.true_value():
            return BaseParserObject.__repr__(self)
        return self.__class__.__name__ + "(dump=" + self.dump(indent=None) + "; true_value=" + self.true_value() + ")"

    def true_value(self) -> str:
        if self.absolute is not None:
            return self.absolute.true_value()
        return self.referenced_object

    @staticmethod
    def resolve_absolute(obj: BaseParserObject) -> BaseParserObject:
        """
        Process an object and return its absolute value if possible.

        :param obj: An object to process.
        :return:
            `obj.absolute` if `obj` is `ReferenceObject` and `absolute` is not None.
            Return `obj` otherwise.
        """
        if isinstance(obj, ReferenceObject):
            return obj.absolute or obj
        return obj

    @staticmethod
    def resolve_expression(obj: Expression) -> Expression:
        """
        Process an object and return its absolute value of :py:class:`~.Expression` if possible.

        :param obj: An object to process.
        :return:
            `obj.absolute` if `obj` is `ReferenceObject` and `absolute` has :py:class:`~.Expression` type.
            Return `obj` otherwise.
        """
        if isinstance(obj, ReferenceObject):
            absolute = obj.absolute
            if isinstance(absolute, Expression):
                return absolute
        return obj


class Python(Expression, Statement):  # type: ignore
    """
    This class is for nodes that cannot be represented by any other classes. It's children contain direct children
    as well as children inside iterable fields.
    """

    def __init__(self, node: tp.Union[ast.expr, ast.stmt]):
        Expression.__init__(self)
        Statement.__init__(self)
        self.parent: tp.Optional[tp.Union[Namespace, Statement, Expression]] = None  # type: ignore
        for key, value in node.__dict__.items():
            if isinstance(value, ast.expr):
                self.add_child(Expression.auto(value), key)
            elif isinstance(value, tp.Iterable):
                for index, child in enumerate(value):
                    if isinstance(child, ast.expr):
                        self.add_child(Expression.auto(child), key + "_" + str(index))
        if unparse.__module__ == "astunparse":
            self.string = unparse(node).strip()
            # astunparse.unparse adds "\n"
            # todo: remove this when python3.8 support is dropped
        else:
            self.string = unparse(node)
        self.type = node.__class__.__name__

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        return self.string

    @classmethod
    def from_str(cls, string: str) -> "Python":
        parsed = ast.parse(string).body
        if len(parsed) != 1:
            raise RuntimeError(f"String {string} should contain only one statement or expression")
        statement = parsed[0]
        if isinstance(statement, ast.stmt):
            return cls(statement)
        elif isinstance(statement, ast.Expr):
            return cls(statement.value)
        else:
            raise RuntimeError(statement)

    @classmethod
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> "Python":  # type: ignore
        return cls(node)
