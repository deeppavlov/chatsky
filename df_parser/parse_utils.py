import logging
import math
from abc import ABC, abstractmethod
import libcst as cst
import typing as tp
from pathlib import Path
import sys
from ruamel.yaml import YAML
import collections
from .distribution_metadata import get_metadata, get_location
import re


def enquote_string(string: str) -> str:
    """Enquote a string."""
    return "'" + re.sub(r"\n[ \t]*", "", string).replace("'", r"\'") + "'"


def evaluate(node: cst.CSTNode) -> str:
    """Evaluate cst Node.

    :param node: cst.Node
    :return: string representing node
    """
    return cst.parse_module("").code_for_node(node)


class CodeBlock(ABC):
    """Block of code."""

    name: str

    @abstractmethod
    def append(self, node: cst.CSTNode) -> None:
        """Append a node to the code block.

        :param node: cst.Node
        :return: None
        """

    @abstractmethod
    def dump(self, output_dir: tp.Union[str, Path]) -> None:
        """Dump code block into file with the name self.name inside the output_dir."""


class ImportBlock(CodeBlock):
    """Block of code with import statements."""

    class ChangeDir:
        """Change 'sys.path' to include the desired path."""

        def __init__(self, path: tp.Union[str, Path]):
            self.path: tp.Union[str, Path] = path

        def __enter__(self):
            sys.path.insert(0, str(self.path))

        def __exit__(self, exc_type, exc_val, exc_tb):
            sys.path.pop(0)

    def __init__(self, working_dir: tp.Union[str, Path], name: str):
        self.imports: tp.Dict[str, tp.DefaultDict[str, tp.List[str]]] = {
            "pypi": collections.defaultdict(list),
            "system": collections.defaultdict(list),
            "local": collections.defaultdict(list),
        }
        self.modules: tp.Dict[str, list] = {}
        self.working_dir: tp.Union[str, Path] = working_dir
        self.name = name
        self.names: tp.List[str] = []
        logging.debug(f"Created ImportBlock with working_dir={working_dir}, name={name}")

    def _find_module(self, module: str) -> list:
        with ImportBlock.ChangeDir(self.working_dir):
            # find vcs or pypi info
            metadata = get_metadata(module)

            if metadata is not None:
                return self.imports["pypi"][metadata]

            # find modules in system modules
            if module in sys.modules.keys():
                return self.imports["system"][module]

            # find locally installed modules
            location = get_location(module, self.working_dir)
            if location:
                return self.imports["local"][location]

            raise RuntimeError(
                f"Module {module} not found in neither {self.working_dir}" f" nor system modules nor installed packages"
            )

    def _add_import(self, module: str, code: str) -> None:
        """Add import to self.imports.

        Add (key, value) pair to the dict:

        * self.imports["pypi"] if the module is available via pip.
        * self.imports["system"] if the module is in 'sys.modules'.
        * self.imports["local"] if the module is stored locally.

        Added key is additional information about module:

        * "pypi": package information, e.g., "df_engine==0.9.0".
        * "system": module name.
        * "local": path to the file. The path is relative to the self.working_dir if possible, absolute otherwise.

        Added value is the line of code that imports the module.

        :param module: str, Name of the module to import, e.g., df_engine.
        :param code: str, Code that imports the module

        :return: None
        """
        module = module.split(".")[0]
        if module not in self.modules.keys():
            self.modules[module] = self._find_module(module)
        self.modules[module].append(code)
        return

    def append(self, node: cst.CSTNode):
        if isinstance(node, cst.Import):
            for name in node.names:
                code = evaluate(cst.Import(names=[name.with_changes(comma=cst.MaybeSentinel.DEFAULT)]))
                self._add_import(name.evaluated_name, code)
        elif isinstance(node, cst.ImportFrom):
            if isinstance(node.names, cst.ImportStar):
                raise RuntimeError(f"ImportStar is not allowed: {evaluate(node)}")
            if node.module:
                code = evaluate(node)
                self._add_import(evaluate(node.module), code)
            else:
                for name in node.names:
                    code = evaluate(cst.Import(names=[name.with_changes(comma=cst.MaybeSentinel.DEFAULT)]))
                    self._add_import(name.evaluated_name, code)
        else:
            raise TypeError(f"Not an import: {evaluate(node)}")

    def dump(self, output_dir: tp.Union[str, Path]):
        ruyaml = YAML()
        ruyaml.width = math.inf  # type: ignore
        imports = dict(
            pypi=dict(self.imports["pypi"]),
            system=dict(self.imports["system"]),
            local=dict(self.imports["local"]),
        )
        with open(Path(output_dir) / self.name, "w") as f:
            ruyaml.dump(imports, f)

    def __iter__(self):
        for key in self.imports.keys():
            for module in self.imports[key].keys():
                for code in self.imports[key][module]:
                    yield code
