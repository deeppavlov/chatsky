"""
Yaml
----
This module defines an object for writing and reading yaml files and a configuration for that object.
"""
from math import inf

try:
    from ruamel.yaml import YAML
except ImportError:
    raise ImportError("Module `ruamel.yaml` is not installed. Install it with `pip install dff[parser]`.")

yaml = YAML()

yaml.width = inf  # type: ignore
