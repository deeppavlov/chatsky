"""This module contains a yaml dumper | loader
"""
from math import inf

from ruamel.yaml import YAML

from df_script_parser.utils.code_wrappers import String, Python
from df_script_parser.utils.namespaces import NamespaceTag, From, Import, AltName, ActorTag, Call

yaml_dumper_loader = YAML()

yaml_dumper_loader.register_class(String)
yaml_dumper_loader.register_class(Python)
yaml_dumper_loader.register_class(NamespaceTag)
yaml_dumper_loader.register_class(From)
yaml_dumper_loader.register_class(Import)
yaml_dumper_loader.register_class(AltName)
yaml_dumper_loader.register_class(ActorTag)
yaml_dumper_loader.register_class(Call)

yaml_dumper_loader.width = inf  # type: ignore
