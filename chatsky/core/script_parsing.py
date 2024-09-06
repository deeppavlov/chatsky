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
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


logger = logging.getLogger(__name__)


class JSONImportError(Exception):
    __notes__ = ["Please read the guide on YAML-formatted scripts: url here"]  # todo: update placeholder string


class JSONImporter:
    CHATSKY_NAMESPACE_PREFIX: str = "chatsky."
    CUSTOM_DIR_NAMESPACE_PREFIX: str = "custom."

    def __init__(self, custom_dir: Union[str, Path]):
        self.custom_dir: Path = Path(custom_dir).absolute()
        self.custom_dir_location: str = str(self.custom_dir.parent)
        self.custom_dir_stem: str = str(self.custom_dir.stem)

    @staticmethod
    def is_resolvable(value: str) -> bool:
        return value.startswith(JSONImporter.CHATSKY_NAMESPACE_PREFIX) or value.startswith(
            JSONImporter.CUSTOM_DIR_NAMESPACE_PREFIX
        )

    @staticmethod
    @contextmanager
    def sys_path_append(path):
        sys_path = sys.path.copy()
        sys.path.append(path)
        yield
        sys.path = sys_path

    @staticmethod
    def replace_prefix(string, old_prefix, new_prefix):
        if not string.startswith(old_prefix):
            raise ValueError(f"String {string!r} does not start with {old_prefix!r}")
        return new_prefix + string[len(old_prefix) :]  # noqa: E203

    def resolve_string_reference(self, obj: str) -> Any:
        # prepare obj string
        if obj.startswith(self.CUSTOM_DIR_NAMESPACE_PREFIX):
            if not self.custom_dir.exists():
                raise JSONImportError(f"Could not find directory {self.custom_dir}")
            obj = self.replace_prefix(obj, self.CUSTOM_DIR_NAMESPACE_PREFIX, self.custom_dir_stem + ".")

        elif obj.startswith(self.CHATSKY_NAMESPACE_PREFIX):
            obj = self.replace_prefix(obj, self.CHATSKY_NAMESPACE_PREFIX, "chatsky.")

        else:
            raise RuntimeError()

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
        args = []
        kwargs = {}
        if isinstance(value, dict):
            for k, v in value.items():
                kwargs[k] = self.replace_resolvable_objects(v)
        elif isinstance(value, list):
            for item in value:
                args.append(self.replace_resolvable_objects(item))
        elif value is not None:  # none is used when no argument is passed: e.g. `dst.Previous:` does not accept args
            args.append(self.replace_resolvable_objects(value))

        return args, kwargs

    def replace_resolvable_objects(self, obj: JsonValue) -> Any:
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
        file = Path(file).absolute()

        with open(file, "r", encoding="utf-8") as fd:
            if file.suffix == ".json":
                pipeline = json.load(fd)
            elif file.suffix in (".yaml", ".yml"):
                pipeline = yaml.load(fd, Loader=Loader)
            else:
                raise JSONImportError("File should have a `.json`, `.yaml` or `.yml` extension")
        if not isinstance(pipeline, dict):
            raise JSONImportError("File should contain a dict")

        logger.info(f"Loaded file {file}")
        return self.replace_resolvable_objects(pipeline)


def get_chatsky_objects():
    def get_objects_from_submodule(submodule_name: str, alias: Optional[str] = None):
        module = importlib.import_module(submodule_name)

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
            # "chatsky.stats",
            # "chatsky.utils",
        )
        for k, v in get_objects_from_submodule(module)
    }
