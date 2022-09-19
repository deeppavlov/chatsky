"""This module contains a parser that recursively parses all the files imported in a root file
"""
import logging
import typing as tp
from pathlib import Path

import libcst as cst

from df_script_parser.processors.parse import Parser
from df_script_parser.utils.code_wrappers import Python, String
from df_script_parser.utils.convenience_functions import get_module_name, remove_suffix
from df_script_parser.utils.exceptions import (
    KeyNotFoundError,
    NamespaceNotParsedError,
    ObjectNotFoundError,
    ResolutionError,
    ParserError,
    ScriptValidationError,
)
from df_script_parser.utils.module_metadata import ModuleType
from df_script_parser.utils.namespaces import Namespace, NamespaceTag, Request, Import, Call
from df_script_parser.utils.validators import check_file_structure, validate_path


ScriptDict = tp.Dict[tp.Union[Python, String], tp.Union["ScriptDict", Python, String]]  # type: ignore


class RecursiveParser:
    """Parse multiple files inside project root dir starting with the root file

    :param project_root_dir: Root directory of a project
    :type project_root_dir: :py:class:`pathlib.Path`
    """

    def __init__(
        self,
        project_root_dir: Path,
    ):
        self.project_root_dir = Path(project_root_dir).absolute()
        self.requirements: tp.List[str] = []
        self.namespaces: tp.Dict[NamespaceTag, tp.Union[Namespace, None]] = {}
        self.unprocessed: tp.List[NamespaceTag] = []
        self.script: tp.Optional[Python] = None
        self.start_label: tp.Optional[tp.Tuple[tp.Union[Python, String]]] = None
        self.fallback_label: tp.Optional[tp.Tuple[tp.Union[Python, String]]] = None

    def resolve_name(
        self,
        name: tp.Union[Request, String, Python],
    ) -> tp.Union[String, Python, dict, Call]:
        """Try to resolve ``name``. Return ``name`` if not possible

        :param name: Name to resolve
        :type name: :py:class:`.String` | :py:class:`.Python`
        :return:
        """
        if isinstance(name, Request):
            return self.get_object(name)
        try:
            if isinstance(name, Python):
                return self.get_object(Request.from_str(name.absolute_value))
        except ResolutionError:
            pass
        return name

    def get_object(self, request: Request) -> tp.Union[dict, Call, Python, String]:
        """Return an object requested in ``request``

        :param request: Request of an object
        :type request: :py:class:`df_script_parser.utils.namespaces.Request`
        :return: Object requested in a ``request``
        :rtype: dict

        :raise :py:exc:`df_script_parser.exceptions.ObjectNotFoundError`:
            If a requested object is not found
        """
        for i in reversed(range(1, len(request.attributes))):
            try:
                left = request.attributes[:i]
                middle = request.attributes[i]
                right = request.attributes[i + 1 :]  # noqa: E203
                potential_namespace = NamespaceTag(".".join(map(repr, left)))
                namespace = self.namespaces.get(potential_namespace)
                if namespace is None:
                    raise NamespaceNotParsedError(f"Not found namespace {repr(potential_namespace)}, request={request}")
                name: tp.Union[dict, Call, Python, String, None] = namespace.names.get(middle)
                if isinstance(name, Python):
                    name = self.get_object(Request.from_str(".".join([name.absolute_value, *map(repr, right)])))

                # process indices
                for index in request.indices:
                    if isinstance(name, dict):
                        resolved_names = {self.resolve_name(k): k for k in name.keys()}
                        key = resolved_names.get(self.resolve_name(index))
                        if key is None:
                            raise ResolutionError(f"Key not found: '{key}', existing keys: {resolved_names}")
                        name = name[key]
                if name is None:
                    raise ObjectNotFoundError(
                        f"Not found {request.attributes[-1]} in {potential_namespace}, request={request}"
                    )
                return name
            except ResolutionError as error:
                logging.debug("Name not found reason: %s", error)
        raise ResolutionError(f"Cannot find object {request}")

    def traverse_dict(
        self,
        script: ScriptDict,
        func: tp.Callable[[tp.List[tp.Union[Python, String]], tp.Union[Python, String, Call]], None],
        traversed_path: tp.Optional[tp.List[tp.Union[Python, String]]] = None,
    ):
        """Traverse a dictionary as a tree call ``func`` at leaf nodes of a tree

        :param script: Dictionary to traverse
        :type script: :py:class:`.ScriptDict`
        :param func: Function to be called
        :type func:
            Callable[[list[:py:class:`.Python` | :py:class:`.String`], :py:class:`.Python` | :py:class:`.String`], None]
        :param traversed_path: Path to the current node, defaults to None
        :type traversed_path: list[:py:class:`.Python` | :py:class:`.String`], optional
        :return: None
        """
        if traversed_path is None:
            traversed_path = []
        for key in script:
            value = script[key]
            while isinstance(value, Python):
                absolute_value = value.absolute_value
                try:
                    value = self.get_object(Request.from_str(absolute_value))
                except ResolutionError:
                    logging.debug("Cannot resolve request: %s", absolute_value)
                    break
            if isinstance(value, dict):
                self.traverse_dict(value, func, traversed_path + [key])
            else:
                func(traversed_path + [key], value)

    def check_node_existence(
        self,
        script: ScriptDict,
        path: tp.List[tp.Union[String, Python]],
    ) -> tp.Union[Import, dict, Python, Call, String]:
        """Check that the path is valid in the script

        :param script: Dict to check
        :type script: :py:class:`.ScriptDict`
        :param path: Path to check
        :type path: list[:py:class:`.Python` | :py:class:`.String`]
        :return: Value that the ``path`` points at
        :rtype: :py:class:`.Import` | dict | :py:class:`.Python` | :py:class:`.Call` | :py:class:`.String`
        """
        value: tp.Union[ScriptDict, Import, Python, Call, String] = script
        for key in path:
            if isinstance(value, Python):
                value = self.get_object(Request.from_str(value.absolute_value))
            if not isinstance(value, dict):
                raise ResolutionError(f"Object {value} is not a dict.")

            resolved_names = {self.resolve_name(k): k for k in value.keys()}
            resolved_key = self.resolve_name(key)
            dict_key = resolved_names.get(resolved_key)

            if dict_key is None:
                raise KeyNotFoundError(f"Not found '{resolved_key}' in '{resolved_names.keys()}'")
            value = value[dict_key]
        return value

    def check_actor_args(self, actor_args: dict):
        """Checks :py:class:`~df_engine.core.actor.Actor` args for correctness

        :param actor_args: Arguments of the :py:class:`~df_engine.core.actor.Actor` call
        :type actor_args: dict
        :return: None
        """
        script = actor_args.get("script")
        if script is None:
            raise ScriptValidationError("Actor call should have a ``script`` argument")
        start_label = actor_args.get("start_label")
        if start_label is None:
            raise ScriptValidationError("Actor call should have a ``start_label`` argument")
        fallback_label = actor_args.get("fallback_label")

        if not isinstance(script, dict):
            if not isinstance(script, Python):
                raise RuntimeError(f"Script argument in actor is not a Python instance: {script}")
            script_request = Request.from_str(script.absolute_value)
            script = self.get_object(script_request)
            if not isinstance(script, dict):
                raise RuntimeError(f"Script is not a dict: {script}")

        self.traverse_dict(script, validate_path)

        for label in [start_label, fallback_label]:
            if label:
                if not isinstance(label, tuple):
                    raise RuntimeError(f"Label is not a tuple: {label}")
                self.check_node_existence(script, list(label))

    def process_import(self, module_type: ModuleType, module_metadata: str) -> tp.Optional[Namespace]:
        """Import module hook for :py:class:`.Namespace`

        Adds distribution metadata to requirements. Parses local files

        :param module_type:
        :param module_metadata:
        :return: new namespace, optional
        """
        if module_type == ModuleType.PIP and module_metadata not in self.requirements:
            self.requirements.append(module_metadata)
        if module_type == ModuleType.LOCAL:
            module_name = get_module_name(Path(module_metadata), self.project_root_dir)

            tag = NamespaceTag(module_name, remove_suffix(module_name, ".__init__"))

            if tag not in self.namespaces or self.namespaces[tag] is None:

                namespace = self.namespaces[tag] = Namespace(
                    Path(module_metadata), self.project_root_dir, self.process_import, self.check_actor_args
                )

                try:
                    self.fill_namespace_from_file(Path(module_metadata).absolute(), namespace)
                    logging.info("Added namespace %s", namespace.name)
                    return namespace
                except ParserError as error:
                    self.unprocessed.append(tag)
                    logging.warning("File %s not included: %s", module_metadata, error)
        return None

    def fill_namespace_from_file(self, file: Path, namespace: Namespace) -> Parser:
        """Parse a file, add its contents to a namespace

        :param file:
        :param namespace:
        :return:
        """
        # Add parent init files to namespaces
        path_to_file = Path(file).absolute().parent.relative_to(self.project_root_dir.parent).parts

        for path_index in range(len(path_to_file)):
            init_file = self.project_root_dir.parent.joinpath(*path_to_file[: path_index + 1]) / "__init__.py"
            module_name = get_module_name(init_file, self.project_root_dir)

            tag = NamespaceTag(module_name, remove_suffix(module_name, ".__init__"))
            if init_file.exists() and tag not in self.namespaces:
                self.namespaces[tag] = None

        # Parse file contents
        with open(file, "r", encoding="utf-8") as input_file:
            py_contents = input_file.read()

        parsed_file = cst.parse_module(py_contents)

        transformer = Parser(self.project_root_dir, namespace)

        check_file_structure(parsed_file.visit(transformer))
        return transformer

    def parse_project_dir(self, starting_from_file: Path) -> dict:
        """Parse a file, mark it as a Root file.

        :param starting_from_file:
        :return:
        """
        starting_from_file = Path(starting_from_file).absolute()
        module_name = get_module_name(starting_from_file, self.project_root_dir)

        tag = NamespaceTag(module_name, remove_suffix(module_name, ".__init__"))
        namespace = self.namespaces[tag] = Namespace(
            starting_from_file, self.project_root_dir, self.process_import, self.check_actor_args
        )

        self.fill_namespace_from_file(starting_from_file, namespace)

        return self.to_dict()

    def to_dict(self) -> dict:
        """Represent everything collected by :py:class:`.RecursiveParser` in a dictionary

        :return: Dictionary with project requirements and collected namespaces
        :rtype: dict
        """
        return {
            "requirements": self.requirements,
            "namespaces": {k: v.names if v else {} for k, v in self.namespaces.items() if k not in self.unprocessed},
        }
