from typing import Union, Optional, Sequence
import importlib
import importlib.util
import importlib.machinery
import sys
import logging
from pathlib import Path
import json
from inspect import ismodule

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
    DFF_NAMESPACE_PREFIX = "dff"
    CUSTOM_DIR_NAMESPACE_PREFIX = "custom_dir"
    CUSTOM_DIR_CONFIG_OPTION = "custom_dir"
    TRANSITIONS_KEY = "TRANSITIONS"
    CONFIG_KEY = "CONFIG"
    TRANSITION_ITEM_KEYS = {"lbl", "cnd"}

    def __init__(self, file: Union[str, Path]):
        if isinstance(file, str):
            file = Path(file)

        if file.suffix == ".json":
            with open(file, "r") as fd:
                script = json.load(fd)
        elif file.suffix in (".yaml", ".yml"):
            with open(file, "r") as fd:
                script = yaml.load(fd, Loader=Loader)
        else:
            raise JSONImportError("File should have a `.json`, `.yaml` or `.yml` extension")
        logger.info(f"Loaded file {file}")

        self.script = script
        config = self.script.get(self.CONFIG_KEY)
        if not isinstance(config, dict):
            raise JSONImportError("Config is not found -- your script has to define a CONFIG dictionary")
        self.config = config

        custom_dir = config.get(self.CUSTOM_DIR_CONFIG_OPTION)
        if custom_dir is not None:
            if not isinstance(custom_dir, str):
                raise JSONImportError("custom_dir must be a string")
            custom_dir_path = Path(custom_dir)
            if not custom_dir_path.is_absolute():
                custom_dir_path = (file.parent / custom_dir_path).resolve(strict=False)

            if not custom_dir_path.exists():
                raise JSONImportError(f"Could not find directory {custom_dir_path}. custom_dir: {custom_dir}")

            logger.info(f"custom_dir set to {custom_dir_path}")

            self._custom_dir_stem = str(custom_dir_path.stem)
            self._custom_dir_location = str(custom_dir_path.parent)
        else:
            self._custom_dir_location = None
        self._custom_modules = {}

    @staticmethod
    def is_resolvable(value: str) -> bool:
        return value.startswith(JSONImporter.DFF_NAMESPACE_PREFIX + ".") or\
               value.startswith(JSONImporter.CUSTOM_DIR_NAMESPACE_PREFIX + ".")

    def import_custom_module(self, module_name: str, paths: Optional[Sequence[str]] = None):
        if module_name in self._custom_modules:
            return self._custom_modules[module_name]

        if paths is None:
            if self._custom_dir_location is None:
                raise JSONImportError("custom_dir option must be set in order to use objects from it")
            paths = [self._custom_dir_location]

        parent_name, _, child_name = module_name.rpartition(".")

        if parent_name:
            parent_module = self.import_custom_module(parent_name, paths)

            paths = parent_module.__spec__.submodule_search_locations
        else:
            # root level import; replace `custom_dir` with actual module name
            if child_name != self.CUSTOM_DIR_NAMESPACE_PREFIX:
                raise RuntimeError(f"Trying to import from custom_dir while using wrong module_name: {child_name!r}")
            child_name = self._custom_dir_stem

        for finder in sys.meta_path:
            spec = finder.find_spec(child_name, paths)
            if spec is not None:
                break
        else:
            raise ModuleNotFoundError(f"No module named {child_name!r} at {paths!r}")

        module = importlib.util.module_from_spec(spec)
        self._custom_modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def resolve_target_object(self, obj: str):
        module_name, _, obj_name = obj.rpartition(".")

        if obj.startswith(self.DFF_NAMESPACE_PREFIX):
            module = importlib.import_module(module_name)
        else:
            module = self.import_custom_module(module_name)
        return getattr(module, obj_name)

    def import_script(self):
        return self.replace_script_objects(self.script)

    def replace_obj(self, obj: JsonValue):
        if not isinstance(obj, dict):
            raise JSONImportError(f"DFF object has to be a dictionary: {obj}")
        keys = obj.keys()
        if len(keys) != 1:
            raise JSONImportError(f"DFF object has to have only 1 key: {obj.keys()}")
        key = keys.__iter__().__next__()
        logger.debug(f"Replacing object: {key}")
        target_obj = self.resolve_target_object(key)

        if target_obj is None:
            raise ImportError(f"Could not find object {key}")

        if not callable(target_obj):
            raise JSONImportError(f"Object `{key}` has to be callable")

        args = []
        kwargs = {}
        if isinstance(obj[key], dict):
            for k, v in obj[key].items():
                kwargs[k] = self.replace_script_objects(v)
        elif isinstance(obj[key], list):
            for item in obj[key]:
                args.append(self.replace_script_objects(item))
        elif obj[key] is not None:
            args.append(self.replace_script_objects(obj[key]))

        return target_obj(*args, **kwargs)

    def process_transitions(self, transition_list: list):
        if not isinstance(transition_list, list):
            raise JSONImportError(f"Transitions value should be a list of dictionaries, not {transition_list}")

        transitions = {}
        for item in transition_list:
            if not isinstance(item, dict):
                raise JSONImportError(f"Transition items have to be dictionaries, not {item}")
            if item.keys() != self.TRANSITION_ITEM_KEYS:
                raise JSONImportError(f"Transition items' keys have to be `lbl` and `cnd`, not {item.keys()}")

            lbl = self.replace_script_objects(item["lbl"])
            if isinstance(lbl, list):
                lbl = tuple(lbl)
            cnd = self.replace_script_objects(item["cnd"])

            if isinstance(lbl, tuple) and lbl in transitions:
                raise JSONImportError(f"Label {lbl} already exists in {transitions}")

            transitions[lbl] = cnd
        return transitions

    def replace_string_values(self, obj: JsonValue):
        if not isinstance(obj, str):
            raise JSONImportError(f"Obj {obj} has to be a string")
        if self.is_resolvable(obj):
            target_obj = self.resolve_target_object(obj)

            if target_obj is None:
                raise JSONImportError(f"Could not find object {obj}")

            return target_obj
        raise RuntimeError()

    def replace_script_objects(self, obj: JsonValue):
        if isinstance(obj, dict):
            keys = obj.keys()
            if len(keys) == 1:
                key = keys.__iter__().__next__()
                if self.is_resolvable(key):
                    return self.replace_obj(obj)

            return {k: (
                self.replace_script_objects(v) if k != self.TRANSITIONS_KEY else self.process_transitions(v)
            ) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.replace_script_objects(item) for item in obj]
        elif isinstance(obj, str):
            if self.is_resolvable(obj):
                return self.replace_string_values(obj)
        return obj


def get_dff_objects():
    def get_objects_from_submodule(submodule_name: str, alias: Optional[str] = None):
        module = importlib.import_module(submodule_name)

        return {
            ".".join([alias or submodule_name, name]): obj
            for name, obj in module.__dict__.items() if not name.startswith("_") and not ismodule(obj)
        }

    return {
        **get_objects_from_submodule("dff.cnd"),
        **get_objects_from_submodule("dff.rsp"),
        **get_objects_from_submodule("dff.lbl"),
        **get_objects_from_submodule("dff.msg", "dff"),
    }
