import libcst as cst
import typing as tp
from .parse_utils import evaluate
import re
from .dumpers_loaders import (
    String,
    Python,
    Start,
    StartString,
    StartPython,
    Fallback,
    FallbackString,
    FallbackPython,
)
from collections import OrderedDict
from pyflakes.api import check
from pyflakes.reporter import Reporter
from os import devnull
import logging


class NodeProcessor:
    def __init__(
        self,
        start_node: cst.CSTNode,
        imports: tp.List[str],
        start_label: tp.List[tp.Any] = None,
        fallback_label: tp.List[tp.Any] = None,
        parse_tuples: bool = False,
        safe_mode: bool = True,
    ):
        """Process cst.Dict. Return a python object.

        :param start_node: CSTNode, Node to process
        :param imports: List[str], List of lines of code with import statements preceding the node
        :param start_label: List[Any], List of dictionary keys, represents a path to the start node
        :param fallback_label: List[Any], List of dictionary keys, represents a path to the fallback node
        :param parse_tuples: bool, If true parse tuples as well
        :param safe_mode: bool, If false doesn't check for ambiguity.
         Set to false only if there are no strings in your code that have the value that might be python code.
        """
        self.imports = imports
        self.start_label = list(start_label) if start_label else None
        self.fallback_label = list(fallback_label) if fallback_label else None
        self.parse_tuples = parse_tuples
        self.safe_mode = safe_mode
        self.stack: tp.List[tp.Any] = []
        logging.info(f"start_label: {start_label}, fallback_label: {fallback_label}")
        self.result = self._process_node(start_node)

    def _process_node(self, node: cst.CSTNode) -> tp.Any:
        """Process a node. Return a python object.

        Processing rules:

        * If a node is a dictionary, return a dict with its keys and values processed.
        * If a node is a list, return a list with its values processed.
        * If a node is a tuple and self.parse_tuples, return a tuple with its values processed.
        * If a node is a BasicString and self.safe_mode, check for string ambiguity -- check if the string could be python code. If it could return a String instance. Also check if the string is a start or a fallback node. Return an instance of the Start or the Fallback class. Return a string otherwise
        * Otherwise check if the node could be a start or fallback node. If so return an instance of the Start or Fallback class else return a str.
        """
        # dict
        if isinstance(node, cst.Dict):
            result = OrderedDict()
            for element in node.elements:
                assert isinstance(element, cst.DictElement), "Starred dict elements are not supported"
                key = self._process_node(element.key)
                self.stack.append(key)
                result[key] = self._process_node(element.value)
                self.stack.pop()
            return dict(result)

        # list
        if isinstance(node, cst.List):
            result = []
            for element in node.elements:
                assert isinstance(element, cst.Element), "Starred elements are not supported"
                result.append(self._process_node(element.value))
            return result

        # tuple
        if self.parse_tuples and isinstance(node, cst.Tuple):
            result = []
            for element in node.elements:
                assert isinstance(element, cst.Element), "Starred elements are not supported"
                result.append(self._process_node(element.value))
            return tuple(result)

        # str
        if isinstance(node, cst.SimpleString):
            value = node.evaluated_value
            # ambiguous str
            if self.safe_mode and is_correct(self.imports, value):
                logging.info(f"Comparing paths: {self.stack + [String(value)]}")
                if self.stack + [String(value)] == self.start_label:
                    logging.info("StartString")
                    return StartString(value)
                if self.stack + [String(value)] == self.fallback_label:
                    logging.info("FallbackString")
                    return FallbackString(value)
                logging.info("String")
                return String(value)
        else:
            value = re.sub(r"\n[ \t]*", "", evaluate(node))

        logging.info(f"Comparing paths: {self.stack + [value]}")
        if self.stack + [value] == self.start_label:
            logging.info("Start")
            return Start(value)
        if self.stack + [value] == self.fallback_label:
            logging.info("Fallback")
            return Fallback(value)
        logging.info("None")
        return value


class Disambiguator:
    def __init__(self, script: dict, imports: tp.List[str]):
        """Process a dict. Return a dict with strings replaced with a subclass of StringTag.
        Store a start_label and a fallback_label paths if a corresponding StringTag was found.

        :param imports: List[str], List of lines of code with import statements which are used to determine a subclass
        """
        self.imports = imports
        self.stack: tp.List[tp.Any] = []
        self.start_label: tp.Optional[tp.List[tp.Any]] = None
        self.fallback_label: tp.Optional[tp.List[tp.Any]] = None
        self.result = self._convert(script)

    def _convert(self, obj: tp.Any) -> tp.Any:
        """Recursively replace all str instances inside os an obj with a correct StringTag subclass instance.

        Replacement rules:

        * If obj is a dict return a dict with all of its keys and values converted.
        * If obj is a list return a list with all of its values converted.
        * If obj is an instance of Start of Fallback classes or their subclasses store current path (as given by self.stack) in either self.start_label or self.fallback_label
        * If obj is an instance of str or Start or Fallback classes return either an instance of String or Python class or their subclasses. If the string is a correct python code given self.imports return a Python or its subclass instance else return a String or its subclass instance.
        """
        # ordered dict
        if isinstance(obj, dict):
            result = OrderedDict()
            for key in obj.keys():
                new_key = self._convert(key)
                self.stack.append(new_key)
                result[new_key] = self._convert(obj[key])
                self.stack.pop()
            return dict(result)

        # list
        if isinstance(obj, list):
            result = []
            for el in obj:
                result.append(self._convert(el))
            return result

        # str
        if isinstance(obj, str):
            return Python(obj) if is_correct(self.imports, obj) else String(obj)

        # start
        if isinstance(obj, Start):
            if not isinstance(obj, (StartString, StartPython)):
                obj = StartPython(obj.value) if is_correct(self.imports, obj.value) else StartString(obj.value)
            self.start_label = self.stack + [obj]
            return obj

        # fallback
        if isinstance(obj, Fallback):
            if not isinstance(obj, (FallbackString, FallbackPython)):
                obj = FallbackPython(obj.value) if is_correct(self.imports, obj.value) else FallbackString(obj.value)
            self.fallback_label = self.stack + [obj]
            return obj

        return obj


def names_from_imports(imports: tp.List[str]) -> tp.List[str]:
    """Extract list of available names from a list of imports.

    example
    -------

    names_from_imports(["from a import b, c", "import d"]) = ["b", "c", "d"]
    """
    result = []
    for import_string in imports:
        node = cst.parse_module(import_string).body[0].body[0]
        if isinstance(node, cst.Import):
            for name in node.names:
                result.append(name.evaluated_alias if name.asname else name.evaluated_name)
        elif isinstance(node, cst.ImportFrom):
            for name in node.names:
                result.append(name.evaluated_alias if name.asname else name.evaluated_name)
        else:
            raise RuntimeError(f"'{import_string}' is not an import")
    return result


def is_correct(imports: tp.List[str], code: str) -> bool:
    """Return true if code is correct by flake w.r.t. imports."""
    code_string = "\n".join([*imports, *names_from_imports(imports), code])
    with open(devnull, "w") as null:
        return check(code_string, "", Reporter(null, null)) == 0
