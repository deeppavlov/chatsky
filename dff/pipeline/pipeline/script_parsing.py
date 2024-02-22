from typing import Union, Dict, Optional
import importlib
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
    DFF_NAMESPACE_PREFIX = "dff."
    CUSTOM_DIR_CONFIG_OPTION = "custom_dir"
    TRANSITIONS_KEY = "TRANSITIONS"
    CONFIG_KEY = "CONFIG"
    TRANSITION_ITEM_KEYS = {"lbl", "cnd"}

    def __init__(self, script: Dict[str, JsonValue]):
        self.script = script
        config = self.script.get(self.CONFIG_KEY)
        if not isinstance(config, dict):
            raise JSONImportError("config is not found -- your script has to define a CONFIG dictionary")
        self.config = config
        custom_dir = config.get(self.CUSTOM_DIR_CONFIG_OPTION, "custom_dir")
        if "." in custom_dir:
            raise JSONImportError("custom dir cannot contain `.`")
        if not Path(custom_dir).exists():
            raise JSONImportError(f"could not find directory {custom_dir}")
        self.custom_dir_prefix = custom_dir + "."

    @staticmethod
    def resolve_target_object(obj: str):
        module_name, object_name = obj.rsplit(".", maxsplit=1)
        module = importlib.import_module(module_name)
        return module.__getattribute__(object_name)

    def import_script(self):
        return self.replace_script_objects(self.script)

    def replace_obj(self, obj: JsonValue):
        if not isinstance(obj, dict):
            raise JSONImportError(f"obj {obj} has to be a dictionary")
        keys = obj.keys()
        if len(keys) != 1:
            raise JSONImportError("obj has to have only 1 key")
        key = keys.__iter__().__next__()
        logger.debug(f"obj: {key}")
        target_obj = self.resolve_target_object(key)

        if target_obj is None:
            raise ImportError(f"Could not find object {key}")

        if not callable(target_obj):
            raise JSONImportError(f"object `{key}` has to be callable")

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
            raise JSONImportError(f"transitions value should be a list of dictionaries, not {transition_list}")

        transitions = {}
        for item in transition_list:
            if not isinstance(item, dict):
                raise JSONImportError(f"transition items have to be dictionaries, not {item}")
            if item.keys() != self.TRANSITION_ITEM_KEYS:
                raise JSONImportError(f"transition items' keys have to be `lbl` and `cnd`, not {item.keys()}")

            lbl = self.replace_script_objects(item["lbl"])
            if isinstance(lbl, list):
                lbl = tuple(lbl)
            cnd = self.replace_script_objects(item["cnd"])

            if isinstance(lbl, tuple) and lbl in transitions:
                raise JSONImportError(f"label {lbl} already exists in {transitions}")

            transitions[lbl] = cnd
        return transitions

    def replace_string_values(self, obj: JsonValue):
        if not isinstance(obj, str):
            raise JSONImportError(f"obj {obj} has to be a string")
        if obj.startswith(self.DFF_NAMESPACE_PREFIX) or obj.startswith(self.custom_dir_prefix):
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
                if key.startswith(self.DFF_NAMESPACE_PREFIX) or key.startswith(self.custom_dir_prefix):
                    return self.replace_obj(obj)

            return {k: (
                self.replace_script_objects(v) if k != self.TRANSITIONS_KEY else self.process_transitions(v)
            ) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.replace_script_objects(item) for item in obj]
        elif isinstance(obj, str):
            if obj.startswith(self.DFF_NAMESPACE_PREFIX) or obj.startswith(self.custom_dir_prefix):
                return self.replace_string_values(obj)
        return obj

    @classmethod
    def from_file(cls, file: Union[str, Path]):
        if isinstance(file, str):
            file = Path(file)

        if file.suffix == ".json":
            with open(file, "r") as fd:
                return cls(json.load(fd))
        elif file.suffix in (".yaml", ".yml"):
            with open(file, "r") as fd:
                return cls(yaml.load(fd, Loader=Loader))
        else:
            raise JSONImportError("file should have a `.json`, `.yaml` or `.yml` extension")


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
