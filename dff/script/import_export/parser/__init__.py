"""This submodule allows import/export of dff projects as yaml or json files
"""

try:
    import libcst  # noqa: F401
    import ruamel.yaml  # noqa: F401
    import pyflakes  # type: ignore  # noqa: F401
    import black  # noqa: F401
except ImportError:
    raise ImportError(
        "Some packages required for `dff.script.import_export.parser` are not found.\n"
        "Install them with `pip install dff[parser]`"
    )

dependencies = {"graph": False}

try:
    import networkx  # type: ignore  # noqa: F401

    dependencies["graph"] = True
except ImportError:
    pass

from dff.script.import_export.parser.cli import (  # noqa: F401, E402
    py2yaml,
    py2yaml_cli,
    yaml2py,
    yaml2py_cli,
    py2graph,
    py2graph_cli,
    graph2py,
    graph2py_cli,
)
