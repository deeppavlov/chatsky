from math import inf

try:
    from ruamel.yaml import YAML
except ImportError:
    raise ImportError(f"Module `ruamel.yaml` is not installed. Install it with `pip install dff[parser]`.")

yaml = YAML()

yaml.width = inf  # type: ignore


def python_factory(base_parser_object):
    return "`" + str(base_parser_object) + "`"
    # return str(base_parser_object)