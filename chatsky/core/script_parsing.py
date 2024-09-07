"""
Pipeline File Import
--------------------
This module introduces tools that allow importing Pipeline objects from
json/yaml files.

- :py:class:`JSONImporter` is a class that imports pipeline from files
- :py:func:`get_chatsky_objects` is a function that provides an index of objects commonly used in a Pipeline definition.
"""

from typing import Union, Optional, Any, List, Tuple
import importlib
import importlib.util
import importlib.machinery
import sys
import logging
from pathlib import Path
import json
from inspect import ismodule
from functools import reduce
from contextlib import contextmanager

from pydantic import JsonValue

try:
    import yaml

    yaml_available = True
except ImportError:
    yaml_available = False


logger = logging.getLogger(__name__)


class JSONImportError(Exception):
    """An exception for incorrect usage of :py:class:`JSONImporter`."""

    __notes__ = [
        "Read the guide on Pipeline import from file: "
        "https://deeppavlov.github.io/chatsky/user_guides/pipeline_import.html"
    ]


class JSONImporter:
    """
    Enables pipeline import from file.

    Since Pipeline and all its components are already pydantic ``BaseModel``,
    the only purpose of this class is to allow importing and instantiating arbitrary objects.

    Import is done by replacing strings of certain patterns with corresponding objects.
    This process is implemented in :py:meth:`resolve_string_reference`.

    Instantiating is done by replacing dictionaries where a single key is an imported object
    with an initialized object where arguments are specified by the dictionary values.
    This process is implemented in :py:meth:`replace_resolvable_objects` and
    :py:meth:`parse_args`.

    :param custom_dir: Path to the directory containing custom code available for import under the
        :py:attr:`CUSTOM_DIR_NAMESPACE_PREFIX`.
    """

    CHATSKY_NAMESPACE_PREFIX: str = "chatsky."
    """
    Prefix that indicates an import from the `chatsky` library.

    This class variable can be changed to allow using a different prefix.
    """
    CUSTOM_DIR_NAMESPACE_PREFIX: str = "custom."
    """
    Prefix that indicates an import from the custom directory.

    This class variable can be changed to allow using a different prefix.
    """
    EXTERNAL_LIB_NAMESPACE_PREFIX: str = "external:"
    """
    Prefix that indicates an import from any library.

    This class variable can be changed to allow using a different prefix.
    """

    def __init__(self, custom_dir: Union[str, Path]):
        self.custom_dir: Path = Path(custom_dir).absolute()
        self.custom_dir_location: str = str(self.custom_dir.parent)
        self.custom_dir_stem: str = str(self.custom_dir.stem)

    @staticmethod
    def is_resolvable(value: str) -> bool:
        """
        Check if ``value`` starts with any of the namespace prefixes:

        - :py:attr:`CHATSKY_NAMESPACE_PREFIX`;
        - :py:attr:`CUSTOM_DIR_NAMESPACE_PREFIX`;
        - :py:attr:`EXTERNAL_LIB_NAMESPACE_PREFIX`.

        :return: Whether the value should be resolved (starts with a namespace prefix).
        """
        return (
            value.startswith(JSONImporter.CHATSKY_NAMESPACE_PREFIX)
            or value.startswith(JSONImporter.CUSTOM_DIR_NAMESPACE_PREFIX)
            or value.startswith(JSONImporter.EXTERNAL_LIB_NAMESPACE_PREFIX)
        )

    @staticmethod
    @contextmanager
    def sys_path_append(path):
        """
        Append ``path`` to ``sys.path`` before yielding and
        restore ``sys.path`` to initial state after returning.
        """
        sys_path = sys.path.copy()
        sys.path.append(path)
        yield
        sys.path = sys_path

    @staticmethod
    def replace_prefix(string, old_prefix, new_prefix) -> str:
        """
        Replace ``old_prefix`` in ``string`` with ``new_prefix``.

        :raises ValueError: If the ``string`` does not begin with ``old_prefix``.
        :return: A new string with a new prefix.
        """
        if not string.startswith(old_prefix):
            raise ValueError(f"String {string!r} does not start with {old_prefix!r}")
        return new_prefix + string[len(old_prefix) :]  # noqa: E203

    def resolve_string_reference(self, obj: str) -> Any:
        """
        Import an object indicated by ``obj``.

        First, ``obj`` is pre-processed -- prefixes are replaced to allow import:

        - :py:attr:`CUSTOM_DIR_NAMESPACE_PREFIX` is replaced ``{stem}.`` where `stem` is the stem of the custom dir;
        - :py:attr:`CHATSKY_NAMESPACE_PREFIX` is replaced with ``chatsky.``;
        - :py:attr:`EXTERNAL_LIB_NAMESPACE_PREFIX` is removed.

        Next the resulting string is imported:
        If the string is ``a.b.c.d``, the following is tried in order:

        1. ``from a import b; return b.c.d``
        2. ``from a.b import c; return c.d``
        3. ``from a.b.c import d; return d``

        For custom dir imports; parent of the custom dir is appended to ``sys.path`` via :py:meth:`sys_path_append`.

        :return: An imported object.
        :raises ValueError: If ``obj`` does not begin with any of the prefixes (is not :py:meth:`is_resolvable`).
        :raises JSONImportError: If a string could not be imported. Includes exceptions raised on every import attempt.
        """
        # prepare obj string
        if obj.startswith(self.CUSTOM_DIR_NAMESPACE_PREFIX):
            if not self.custom_dir.exists():
                raise JSONImportError(f"Could not find directory {self.custom_dir}")
            obj = self.replace_prefix(obj, self.CUSTOM_DIR_NAMESPACE_PREFIX, self.custom_dir_stem + ".")

        elif obj.startswith(self.CHATSKY_NAMESPACE_PREFIX):
            obj = self.replace_prefix(obj, self.CHATSKY_NAMESPACE_PREFIX, "chatsky.")

        elif obj.startswith(self.EXTERNAL_LIB_NAMESPACE_PREFIX):
            obj = self.replace_prefix(obj, self.EXTERNAL_LIB_NAMESPACE_PREFIX, "")

        else:
            raise ValueError(f"Could not find a namespace prefix: {obj}")

        # import obj
        split = obj.split(".")
        exceptions: List[Exception] = []

        for module_split in range(1, len(split)):
            module_name = ".".join(split[:module_split])
            object_name = split[module_split:]
            try:
                with self.sys_path_append(self.custom_dir_location):
                    module = importlib.import_module(module_name)
                return reduce(getattr, [module, *object_name])
            except Exception as exc:
                exceptions.append(exc)
                logger.debug(f"Exception attempting to import {object_name} from {module_name!r}", exc_info=exc)
        raise JSONImportError(f"Could not import {obj}") from Exception(exceptions)

    def parse_args(self, value: JsonValue) -> Tuple[list, dict]:
        """
        Parse ``value`` into args and kwargs:

        - If ``value`` is a dictionary, it is returned as kwargs;
        - If ``value`` is a list, it is returned as args;
        - If ``value`` is ``None``, both args and kwargs are empty;
        - If ``value`` is anything else, it is returned as the only arg.

        :return: A tuple of args and kwargs.
        """
        args = []
        kwargs = {}
        value = self.replace_resolvable_objects(value)
        if isinstance(value, dict):
            kwargs = value
        elif isinstance(value, list):
            args = value
        elif value is not None:  # none is used when no argument is passed: e.g. `dst.Previous:` does not accept args
            args = [value]

        return args, kwargs

    def replace_resolvable_objects(self, obj: JsonValue) -> Any:
        """
        Replace any resolvable objects inside ``obj`` with their resolved versions and
        initialize any that are the only key of a dictionary.

        This method iterates over every value inside ``obj`` (which is ``JsonValue``).
        Any string that :py:meth:`is_resolvable` is replaced with an object return from
        :py:meth:`resolve_string_reference`.
        This is done only once (i.e. if a string is resolved to another resolvable string,
        that string is not resolved).

        Any dictionaries that contain only one resolvable key are replaced with a result of
        ``resolve_string_reference(key)(*args, **kwargs)`` (the object is initialized)
        where ``args`` and ``kwargs`` is the result of :py:meth:`parse_args`
        on the value of the dictionary.

        :return: A new object with replaced resolvable strings and dictionaries.
        """
        if isinstance(obj, dict):
            keys = obj.keys()
            if len(keys) == 1:
                key = keys.__iter__().__next__()
                if self.is_resolvable(key):
                    args, kwargs = self.parse_args(obj[key])
                    return self.resolve_string_reference(key)(*args, **kwargs)

            return {k: (self.replace_resolvable_objects(v)) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.replace_resolvable_objects(item) for item in obj]
        elif isinstance(obj, str):
            if self.is_resolvable(obj):
                return self.resolve_string_reference(obj)
        return obj

    def import_pipeline_file(self, file: Union[str, Path]) -> dict:
        """
        Import a dictionary from a json/yaml file and replace resolvable objects in it.

        :return: A result of :py:meth:`replace_resolvable_objects` on the dictionary.
        :raises JSONImportError: If a file does not have a correct file extension.
        :raises JSONImportError: If an imported object from file is not a dictionary.
        """
        file = Path(file).absolute()

        with open(file, "r", encoding="utf-8") as fd:
            if file.suffix == ".json":
                pipeline = json.load(fd)
            elif file.suffix in (".yaml", ".yml"):
                if not yaml_available:
                    raise ImportError("`pyyaml` package is missing.\nRun `pip install chatsky[yaml]`.")
                pipeline = yaml.safe_load(fd)
            else:
                raise JSONImportError("File should have a `.json`, `.yaml` or `.yml` extension")
        if not isinstance(pipeline, dict):
            raise JSONImportError("File should contain a dict")

        logger.info(f"Loaded file {file}")
        return self.replace_resolvable_objects(pipeline)


def get_chatsky_objects():
    """
    Return an index of most commonly used ``chatsky`` objects (in the context of pipeline initialization).

    :return: A dictionary where keys are names of the objects (e.g. ``chatsky.core.Message``) and values
        are the objects.
        The items in the dictionary are all the objects from the ``__init__`` files of the following modules:

        - "chatsky.cnd";
        - "chatsky.rsp";
        - "chatsky.dst";
        - "chatsky.proc";
        - "chatsky.core";
        - "chatsky.core.service";
        - "chatsky.slots";
        - "chatsky.context_storages";
        - "chatsky.messengers".
    """
    json_importer = JSONImporter(custom_dir="none")

    def get_objects_from_submodule(submodule_name: str, alias: Optional[str] = None):
        module = json_importer.resolve_string_reference(submodule_name)

        return {
            ".".join([alias or submodule_name, name]): obj
            for name, obj in module.__dict__.items()
            if not name.startswith("_") and not ismodule(obj)
        }

    return {
        k: v
        for module in (
            "chatsky.cnd",
            "chatsky.rsp",
            "chatsky.dst",
            "chatsky.proc",
            "chatsky.core",
            "chatsky.core.service",
            "chatsky.slots",
            "chatsky.context_storages",
            "chatsky.messengers",
            # "chatsky.stats",
            # "chatsky.utils",
        )
        for k, v in get_objects_from_submodule(module).items()
    }
