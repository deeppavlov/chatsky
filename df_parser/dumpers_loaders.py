import pprint
from ruamel.yaml import YAML
from math import inf
from .parse_utils import enquote_string


class StringTag:
    yaml_tag = u"!tag"

    def __init__(self, value: str):
        self.value: str = value

    def __hash__(self):
        return self.value.__hash__()

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.value == other.value
        return False

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar(cls.yaml_tag, node.value)

    @classmethod
    def from_yaml(cls, constructor, node):
        return cls(node.value)


class String(StringTag):
    yaml_tag = u"!str"

    def __repr__(self):
        return enquote_string(self.value)


class Python(StringTag):
    yaml_tag = u"!py"


class Start(StringTag):
    yaml_tag = u"!start"


class StartString(Start):
    yaml_tag = u"!start:str"

    def __repr__(self):
        return enquote_string(self.value)


class StartPython(Start):
    yaml_tag = u"!start:py"


class Fallback(StringTag):
    yaml_tag = u"!fallback"


class FallbackString(Fallback):
    yaml_tag = u"!fallback:str"

    def __repr__(self):
        return enquote_string(self.value)


class FallbackPython(Fallback):
    yaml_tag = u"!fallback:py"


ryaml = YAML()

ryaml.register_class(String)
ryaml.register_class(Python)
ryaml.register_class(Start)
ryaml.register_class(StartString)
ryaml.register_class(StartPython)
ryaml.register_class(Fallback)
ryaml.register_class(FallbackString)
ryaml.register_class(FallbackPython)

ryaml.width = inf  # type: ignore


def pp(obj, stream):
    try:
        pprint.pprint(obj, stream, sort_dicts=False)
    except TypeError as e:
        raise Exception("You need python 3.8+ for df_script_parser.yaml2py") from e
