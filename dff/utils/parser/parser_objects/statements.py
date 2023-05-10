"""
Statements
----------
This module defines parser object classes that subclass from :py:class:`~.Statement`.
"""
import typing as tp
import ast
import logging

from dff.utils.parser.parser_objects.base_classes import BaseParserObject, Statement, Expression, ReferenceObject
from dff.utils.parser.utils import is_instance, cached_property, unparse
from dff.utils.parser.exceptions import StarError


logger = logging.getLogger(__name__)


class Import(Statement, ReferenceObject):
    """
    This class if for nodes that represent :py:class:`ast.Import`.
    """

    def __init__(self, module: str, alias: tp.Optional[str] = None):
        ReferenceObject.__init__(self)
        Statement.__init__(self)
        self.module = module
        self.alias = alias

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        return f"import {self.module}" + (f" as {self.alias}" if self.alias else "")

    @cached_property
    def _resolve_once(self) -> tp.Optional[BaseParserObject]:
        namespace_name = self.namespace.resolve_relative_import(self.module)
        namespace = self.dff_project.get_namespace(namespace_name)
        if namespace is None:
            logger.debug(
                f"{self.__class__.__name__} did not resolve: {str(self)}\nNamespace {namespace_name} not found"
            )
            return None
        return namespace

    @cached_property
    def referenced_object(self) -> str:
        return self.namespace.resolve_relative_import(self.module)

    @classmethod
    @tp.overload
    def from_ast(cls, node: ast.Import, **kwargs) -> tp.Dict[str, "Import"]:  # type: ignore
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        """
        Extract imports from ast node.

        :return: A dictionary of statements contained in the node.
            The keys are names under which an object is imported, and the values are instances of this class.
            For example an import statement `import obj_1 as obj, obj_2, obj_3 as obj_3`
            will produce a dictionary with the following items:

                - `(obj, Import(import obj_1 as obj))`
                - `(obj_2, Import(import obj_2))`
                - `(obj_3, Import(import obj_3 as obj_3))`
        """
        if not isinstance(node, ast.Import):
            return None
        result = {}
        for name in node.names:
            result[name.asname or name.name] = cls(name.name, name.asname)
        return result


class ImportFrom(Statement, ReferenceObject):
    """
    This class if for nodes that represent :py:class:`ast.ImportFrom`.
    """

    def __init__(self, module: str, level: int, obj: str, alias: tp.Optional[str] = None):
        ReferenceObject.__init__(self)
        Statement.__init__(self)
        self.module = module
        self.level = level
        self.obj = obj
        self.alias = alias

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        return f"from {self.level * '.' + self.module} import {self.obj}" + (f" as {self.alias}" if self.alias else "")

    @cached_property
    def _resolve_once(self) -> tp.Optional[BaseParserObject]:
        namespace_name = self.namespace.resolve_relative_import(self.module, self.level)
        namespace = self.dff_project.get_namespace(namespace_name)
        if namespace is None:
            logger.debug(
                f"{self.__class__.__name__} did not resolve: {str(self)}\nNamespace {namespace_name} not found"
            )
            return None
        if not is_instance(namespace, "dff.utils.parser.namespace.Namespace"):
            raise RuntimeError(namespace)

        obj = namespace.get_object(self.obj)
        if obj is None:
            logger.debug(
                f"{self.__class__.__name__} did not resolve: {str(self)}\n"
                f"Object {self.obj} not found in namespace {namespace}"
            )
            return None

        return obj

    @cached_property
    def referenced_object(self) -> str:
        resolved = self._resolve_once
        if isinstance(resolved, ReferenceObject):
            return resolved.referenced_object
        if self.level > 0:
            substitute_module_name = self.namespace.resolve_relative_import(self.module, self.level) + "." + self.obj
        else:
            substitute_module_name = self.module + "." + self.obj
        return substitute_module_name

    @classmethod
    @tp.overload
    def from_ast(cls, node: ast.ImportFrom, **kwargs) -> tp.Dict[str, "ImportFrom"]:  # type: ignore
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        """
        Extract from-imports from ast node.

        :return:
            A dictionary of statements contained in the node.
            The keys are names under which an object is imported, and the values are instances of this class.
            For example an import statement `from module import obj_1 as obj, obj_2, obj_3 as obj_3`
            will produce a dictionary with the following items:

                - `(obj, ImportFrom(from module import obj_1 as obj))`
                - `(obj_2, ImportFrom(from module import obj_2))`
                - `(obj_3, ImportFrom(from module import obj_3 as obj_3))`
        """
        if not isinstance(node, ast.ImportFrom):
            return None
        result = {}
        for name in node.names:
            if name.name == "*":
                raise StarError(f"Starred import is not supported: {unparse(node)}")
            result[name.asname or name.name] = cls(node.module or "", node.level, name.name, name.asname)
        return result


class Assignment(Statement):
    """
    This class if for nodes that represent :py:class:`ast.Assign` or :py:class:`ast.AnnAssign`.
    """

    def __init__(self, target: Expression, value: Expression):
        super().__init__()
        self.add_child(target, "target")
        self.add_child(value, "value")

    def dump(self, current_indent: int = 0, indent: tp.Optional[int] = 4) -> str:
        return (
            f"{self.children['target'].dump(current_indent, indent)} ="
            f" {self.children['value'].dump(current_indent, indent)}"
        )

    @classmethod
    @tp.overload
    def from_ast(  # type: ignore
        cls, node: tp.Union[ast.Assign, ast.AnnAssign], **kwargs
    ) -> tp.Dict[str, "Assignment"]:
        ...

    @classmethod
    @tp.overload
    def from_ast(cls, node: tp.Union[ast.stmt, ast.expr], **kwargs) -> None:
        ...

    @classmethod
    def from_ast(cls, node, **kwargs):
        """
        Extract assignments from ast node.

        :return:
            A dictionary of statements contained in the node.
            The keys are names of declared object, and the values are instances of this class.
            For example an assignment statement `a = b = c = 1`
            will produce a dictionary with the following items:

                - `(c, Assignment(c = 1))`
                - `(a, Assignment(a = c))`
                - `(b, Assignment(b = c))`
        """
        if isinstance(node, ast.Assign):
            result = {}
            target = Expression.auto(node.targets[-1])
            value = Expression.auto(node.value)
            result[str(target)] = cls(target=target, value=value)
            for new_target in map(Expression.auto, node.targets[:-1]):
                # todo: add support for tuple targets
                result[str(new_target)] = cls(target=new_target, value=target)
            return result
        if isinstance(node, ast.AnnAssign):
            result = {}
            if node.value is None:
                logger.warning(f"Assignment has no value: {unparse(node)}")
                return None
            target = Expression.auto(node.target)
            value = Expression.auto(node.value)
            result[str(target)] = cls(target=target, value=value)
            return result
        return None
