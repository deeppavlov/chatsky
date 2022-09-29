"""This module contains a class that represents a namespace (list of objects inside a file) as well as some functions
and classes to support it.
"""
import logging
import typing as tp
from pathlib import Path

import libcst as cst
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.constructor import Constructor
from ruamel.yaml.representer import Representer

from df_script_parser.utils.code_wrappers import Python, String
from df_script_parser.utils.convenience_functions import repr_libcst_node, remove_suffix, get_module_name
from df_script_parser.utils.exceptions import ObjectNotFoundError, ResolutionError, RequestParsingError
from df_script_parser.utils.module_metadata import ModuleType, get_module_info


class Import(Python):
    """This class is used to represent an object that is an imported module.

    - :py:attr:`df_script_parser.utils.code_wrappers.StringTag.show_yaml_tag` is set to True
    - :py:attr:`df_script_parser.utils.code_wrappers.StringTag.display_absolute_value` is set to False

    :param module: Name of the module being imported
    :type module: str
    """

    yaml_tag = "!import"

    def __init__(self, module):
        super().__init__(module, show_yaml_tag=True, display_absolute_value=False)

    def __repr__(self):
        return f"import {self.display_value}"


class From(Python):
    """This class is used to represent an object that refers to an object from another module.

    - Concatenation of ``module_name`` and ``obj`` using a whitespace is treated as
      :py:attr:`df_script_parser.utils.code_wrappers.StringTag.display_value`
    - Concatenation of ``module_name`` and ``obj`` using a dot is treated as
      :py:attr:`df_script_parser.utils.code_wrappers.StringTag.absolute_value`
    - :py:attr:`df_script_parser.utils.code_wrappers.StringTag.show_yaml_tag` is set to True
    - :py:attr:`df_script_parser.utils.code_wrappers.StringTag.display_absolute_value` is set to False

    :param module_name: Name of the module from which the object is imported
    :type module_name: str
    :param obj: Object being imported
    :type obj: str
    """

    yaml_tag = "!from"

    def __init__(self, module_name: str, obj: str):
        super().__init__(
            module_name + " " + obj, f"{module_name}.{obj}", show_yaml_tag=True, display_absolute_value=False
        )
        self.module_name = module_name
        self.obj = obj

    def __repr__(self):
        return f"from {self.module_name} import {self.obj}"

    @classmethod
    def from_yaml(cls, constructor: Constructor, node):
        split = node.value.split(" ")
        return cls(split[0], split[1])


class AltName(Python):
    """This class is used to represent an object that refers to another object in the namespace."""


class ActorTag(Python):
    """This class is used as a key in a dictionary for :py:class:`.Call`. To be removed"""

    yaml_tag = "!actor"


class Call:
    """This class is used to represent a function call"""

    yaml_tag = "!call"  # TdOo: replace with actor

    def __init__(self, name: str, args: dict):
        self.name: str = name
        self.args: dict = args

    def __repr__(self):
        return (
            self.name
            + "("
            + ", ".join(repr(value) if isinstance(key, int) else f"{key}={value}" for key, value in self.args.items())
            + ")"
        )

    @classmethod
    def to_yaml(cls, representer: Representer, node: "Call"):
        """Represent object in yaml

        :param representer: Yaml node representer that provide functions for displaying values
        :type representer: :py:class:`ruamel.yaml.representer.Representer`
        :param node: Node that is represented
        :type node: :py:class:`Call`
        :return: Result of :py:meth:`.Representer.represent_mapping`
        """
        return representer.represent_mapping(cls.yaml_tag, {"name": node.name, "args": node.args})

    @classmethod
    def from_yaml(cls, constructor: Constructor, node):
        """Construct the class from yaml

        :param constructor: Yaml constructor of a class
        :type constructor: :py:class:`.Constructor`
        :param node: Yaml node
        :return: Instance of the class
        """
        data = CommentedMap()
        constructor.construct_mapping(node, data, deep=True)  # type: ignore
        return cls(**data)


class NamespaceTag(Python):
    """This class is used to store a name of a namespace.

    - :py:attr:`df_script_parser.utils.code_wrappers.StringTag.show_yaml_tag` is set to False by default
    """

    yaml_tag = "!namespace"

    def __hash__(self):
        return hash(self.absolute_value)

    def __eq__(self, other):
        if isinstance(other, NamespaceTag):
            return self.absolute_value == other.absolute_value
        return False


class Request:
    """Represents a request to an object

    - :py:attr:`Request.attributes` is used to store module name and object name separated by a dot
    - :py:attr:`Request.indices` is used to store a sequence of keys if requested object is an element of a dict

    :param node: Parsed request
    :type node: :py:class:`libcst.CSTNode`
    :param get_absolute_attributes: :py:meth:`Namespace.get_absolute_name_list`
        that is used to get an absolute location of an object
    :type get_absolute_attributes: Callable[[list[:py:class:`df_script_parser.utils.code_wrappers.Python`]],
        list[:py:class:`df_script_parser.utils.code_wrappers.Python`]], optional

    :raise :py:exc:`df_script_parser.utils.exceptions.RequestParsingError`:
        If a node cannot be represented as a request
    """

    def __init__(
        self,
        node: cst.CSTNode,
        get_absolute_attributes: tp.Optional[tp.Callable[[tp.List[Python]], tp.List[Python]]] = None,
    ):
        self.attributes: tp.List[Python] = []
        self.indices: tp.List[tp.Union["Request", Python, String]] = []
        self.get_absolute_attributes = get_absolute_attributes
        self._process_node(node)
        if get_absolute_attributes:
            self.attributes = get_absolute_attributes(self.attributes)

    def _process_node(self, node: cst.CSTNode):
        """Recursively parse a node, fill :py:attr:`Request.attributes` and :py:attr:`Request.indices`

        :param node: Node to parse
        :type node: :py:class:`libcst.CSTNode`

        :raise :py:exc:`df_script_parser.utils.exceptions.RequestParsingError`:
            If a node cannot be represented as a request
        """
        if isinstance(node, cst.Subscript):
            self._process_subscript(node)
        elif isinstance(node, cst.Attribute):
            self._process_attribute(node)
        elif isinstance(node, cst.Name):
            self._process_name(node)
        else:
            # Note: If there are a lot of calls to repr_libcst_node and they hinder performance it's probably here.
            raise RequestParsingError(f"Node {repr_libcst_node(node)} is not a subscript, attribute or name.")

    def _process_subscript(self, node: cst.Subscript):
        """Recursively parse a node that is a Subscript

        :param node: Node to parse
        :type node: :py:class:`libcst.Subscript`

        :raise :py:exc:`df_script_parser.utils.exceptions.RequestParsingError`:
            If a node cannot be represented as a request
        """
        if len(node.slice) != 1:
            raise RequestParsingError(f"Subscript {repr_libcst_node(node)} has multiple slices.")
        index = node.slice[0].slice
        if not isinstance(index, cst.Index):
            raise RequestParsingError(f"Slice {repr_libcst_node(index)} is not an index.")
        try:
            self.indices.insert(0, Request(index.value, self.get_absolute_attributes))
        except RequestParsingError:
            if isinstance(index.value, cst.SimpleString):
                self.indices.insert(0, String(index.value.evaluated_value))
            else:
                self.indices.insert(0, Python(repr_libcst_node(index.value)))
        self._process_node(node.value)

    def _process_attribute(self, node: cst.Attribute):
        """Recursively parse a node that is an Attribute

        :param node: Node to parse
        :type node: :py:class:`libcst.Attribute`

        :raise :py:exc:`df_script_parser.utils.exceptions.RequestParsingError`:
            If a node cannot be represented as a request
        """
        self._process_node(node.value)
        self._process_node(node.attr)

    def _process_name(self, node: cst.Name):
        """Parse a node that is a Name

        :param node: Node to parse
        :type node: :py:class:`libcst.Name`
        """
        self.attributes.append(Python(node.value))

    @classmethod
    def from_str(
        cls, request: str, get_absolute_attributes: tp.Optional[tp.Callable[[tp.List[Python]], tp.List[Python]]] = None
    ):
        """Construct the request class using a string

        :param request: String representing a request
        :type request: str
        :param get_absolute_attributes: :py:meth:`Namespace.get_absolute_name_list`
            that is used to get an absolute location of an object
        :type get_absolute_attributes: Callable[[list[:py:class:`df_script_parser.utils.code_wrappers.Python`]],
            list[:py:class:`df_script_parser.utils.code_wrappers.Python`]], optional

        :raise :py:exc:`df_script_parser.utils.exceptions.RequestParsingError`:
            If a string cannot be represented as a request

        :return: Instance of :py:class:`Request` class
        """
        return cls(cst.parse_expression(request), get_absolute_attributes)

    def __repr__(self):
        return "".join(
            [
                ".".join(map(repr, self.attributes)),
                "[" if len(self.indices) > 0 else "",
                "][".join(map(repr, self.indices)),
                "]" if len(self.indices) > 0 else "",
            ]
        )


class Namespace:
    """This class represents a namespace an all the objects inside it

    :param path: Path to the file containing objects
    :type path: :py:class:`pathlib.Path`
    :param project_root_dir: Root dir of the project, used to get a relative name of the file
    :type project_root_dir: :py:class:`pathlib.Path`
    :param import_module_hook: Function that is being called when an import is added to the namespace, defaults to None
    :type import_module_hook:
        Callable[[:py:class:`.ModuleType`, str], None] | None, optional
    :param actor_args_check: Function that is being called when an instance of :py:class:`df_engine.core.actor.Actor` is
        created, defaults to None
    :type actor_args_check:
        Callable[[dict], None] | None, optional
    """

    def __init__(
        self,
        path: Path,
        project_root_dir: Path,
        import_module_hook: tp.Optional[tp.Callable[[ModuleType, str], tp.Optional["Namespace"]]] = None,
        actor_args_check: tp.Optional[tp.Callable[[dict, tp.List[str]], None]] = None,
    ):
        self.path = Path(path)
        self.project_root_dir = Path(project_root_dir)
        self.name: str = remove_suffix(get_module_name(self.path, self.project_root_dir), ".__init__")
        self.names: tp.Dict[Python, tp.Union[Import, From, Python, Call, dict]] = {}
        self.import_module_hook = import_module_hook
        self.actor_args_check = actor_args_check

    def __iter__(self):
        for name in self.names:
            yield name

    def process_module_import(
        self,
        module_name: str,
    ) -> tp.Tuple[str, tp.Optional["Namespace"]]:
        """Call ``import_module_hook``, return absolute import name for
        :py:attr:`df_script_parser.utils.module_metadata.ModuleType.LOCAL` modules

        :param module_name: Module name
        :type module_name: str
        :return: Newly created namespace and its module name

            - ``module_name`` for :py:attr:`df_script_parser.utils.module_metadata.ModuleType.PIP` and
              :py:attr:`df_script_parser.utils.module_metadata.ModuleType.SYSTEM`
            - Absolute name for :py:attr:`df_script_parser.utils.module_metadata.ModuleType.LOCAL`
        :rtype: tuple[str, :py:class:`.Namespace`]
        """
        module_type, module_metadata = get_module_info(module_name, self.path.parent)
        namespace = None
        if self.import_module_hook:
            namespace = self.import_module_hook(module_type, module_metadata)

        return (
            remove_suffix(get_module_name(Path(module_metadata), self.project_root_dir), ".__init__")
            if module_type is ModuleType.LOCAL
            else module_name,
            namespace,
        )

    def add_import(
        self,
        module_name: str,
        alias: tp.Optional[str] = None,
    ) -> None:
        """Add import to the namespace

        :param module_name: String used to import a module
        :type module_name: str
        :param alias: Alias under which the module is imported
        :type alias: str, optional
        :return: None
        """
        import_object = Import(self.process_module_import(module_name)[0])
        self.names[Python(alias) if alias else Python(module_name)] = import_object

    def add_from_import(
        self,
        module_name: str,
        obj: str,
        alias: tp.Optional[str] = None,
    ) -> None:
        """Add a from-import to the namespace

        :param module_name: Name of the module from which the object is imported
        :type module_name: str
        :param obj: Name of the object
        :type obj: str
        :param alias: Alias under which the object is imported
        :type alias: str, optional
        :return: None
        """
        name, namespace = self.process_module_import(module_name)
        import_object = From(name, obj)
        if namespace:
            if Python(obj) not in namespace.names:
                logging.warning("Object %s not found in %s", obj, namespace.name)
        self.names[Python(alias) if alias else Python(obj)] = import_object

    def add_alt_name(
        self,
        obj: str,
        alias: str,
    ) -> None:
        """Add an alternative name to the object in the namespace

        :param obj: Object to which the alternative name is bound
        :type obj: str
        :param alias: The alternative name
        :type alias: str
        :return: None
        """
        if Python(obj) not in self:
            raise ObjectNotFoundError(f"Not found {obj} in {self.names}")
        self.names[Python(alias)] = AltName(obj, absolute_value=self.get_absolute_name(obj))

    def add_dict(self, name: str, dictionary: dict) -> None:
        """Add a dictionary to the namespace

        :param name: Dictionary name
        :type name: str
        :param dictionary: Dictionary contents
        :type dictionary: dict
        :return:
        """
        self.names[Python(name)] = dictionary

    def add_function_call(
        self,
        name: str,
        func_name: str,
        args: dict,
        check_args: bool = False,
    ):
        """Add a call to :py:class:`df_engine.core.actor.Actor`

        :param name: Name of the actor
        :type name: str
        :param func_name: Name of the function to add
        :type func_name: str
        :param args: Dictionary of arguments of the call
        :type args: dict
        :param check_args:
            Whether to check args for correctness if the function being called is :py:class:`df_engine.core.Actor`,
            defaults to False
        :type check_args: bool
        :return:
        """
        if check_args and self.actor_args_check:
            self.actor_args_check(args, [self.name, name, "script"])
        self.names[ActorTag(name)] = Call(func_name, args)

    def get_absolute_name(self, name: str) -> tp.Optional[str]:
        """Get an absolute variant of a name

        :param name: Name of a local object
        :type name: str
        :return: Absolute name of the object if possible. None otherwise
        :rtype: str, optional
        """
        try:
            return repr(Request.from_str(name, self.get_absolute_name_list))
        except ResolutionError:
            return None

    def get_absolute_name_list(self, names: tp.List[Python]) -> tp.List[Python]:
        """Make an object name absolute

        For example, namespace with added ``import df_engine.core.keywords as kw`` will return
        ``[df_engine, core, keywords, GLOBAL]`` if this method is called with ``[kw, GLOBAL]``

        :param names: List of module and object names
        :type names: list[:py:class:`.Python`]
        :return: Absolute name of the object
        :rtype: list[:py:class:`.code_wrappers.Python`]
        """
        stack = []
        for item in names:
            stack.append(item)
            name = Python(".".join(map(repr, stack)))
            if name in self:
                obj = self.names[name]
                names_left = names[len(stack) :]  # noqa: E203
                while isinstance(obj, AltName):
                    name = obj
                    obj = self.names[Python(name.display_value)]
                if isinstance(obj, From):
                    return list(map(Python, obj.module_name.split(".") + obj.obj.split("."))) + names_left
                if isinstance(obj, Import):
                    return list(map(Python, obj.absolute_value.split("."))) + names_left
                if isinstance(obj, dict):
                    if len(stack) != len(names):
                        raise ResolutionError(
                            f"Attempted access to an attribute {'.'.join(map(repr, names_left))} of a dict {obj}"
                        )
                    return list(map(Python, self.name.split("."))) + [name]
        raise ObjectNotFoundError(f"Not found object {'.'.join(map(repr, names))} in {self.names}")
