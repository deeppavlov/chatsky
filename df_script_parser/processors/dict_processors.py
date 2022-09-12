"""Processors for dicts.
The purpose of these processors is to take a dictionary
and replace all the keys and values that are not dicts, lists or tuples with StringTag instances.
"""
import logging
import re
import typing as tp
from collections import OrderedDict
from os import devnull

import libcst as cst
from pyflakes.api import check  # type: ignore
from pyflakes.reporter import Reporter  # type: ignore

from df_script_parser.utils.code_wrappers import (
    String,
    Python,
)
from df_script_parser.utils.convenience_functions import evaluate
from df_script_parser.utils.exceptions import StarredError
from df_script_parser.utils.namespaces import Namespace


class NodeProcessor:
    """Process :py:class:`.Dict`. Return a python object

    :param namespace: Namespace used to determine if a tag is needed.
    :type namespace: :py:class:`.Namespace`
    :param parse_tuples: If true parse tuples as well, defaults to False
    :type parse_tuples: bool
    """

    def __init__(
        self,
        namespace: Namespace,
        parse_tuples: bool = False,
    ):
        self.namespace: Namespace = namespace
        self.parse_tuples = parse_tuples

    def _process_dict(self, node: cst.Dict) -> dict:
        result = OrderedDict()
        for element in node.elements:
            if not isinstance(element, cst.DictElement):
                raise StarredError("Starred dict elements are not supported")
            key = self._process_node(element.key)
            result[key] = self._process_node(element.value)
        return dict(result)

    def _process_list(self, node: tp.Union[cst.List, cst.Tuple]) -> list:
        result = []
        for element in node.elements:
            if not isinstance(element, cst.Element):
                raise StarredError("Starred elements are not supported")
            result.append(self._process_node(element.value))
        return result

    def _process_node(self, node: cst.CSTNode) -> object:
        if isinstance(node, cst.Dict):
            return self._process_dict(node)

        if isinstance(node, cst.List):
            return self._process_list(node)

        if self.parse_tuples and isinstance(node, cst.Tuple):
            return tuple(self._process_list(node))

        if isinstance(node, cst.SimpleString):
            value = node.evaluated_value
            return String(value, show_yaml_tag=is_correct(list(self.namespace), value))

        value = re.sub(r"\n[ \t]*", "", evaluate(node))

        if not is_correct(list(self.namespace), value):
            logging.warning("Value %s is not a correct line of python code", value)
            return Python(value, self.namespace.get_absolute_name(value), show_yaml_tag=True)

        return Python(value, self.namespace.get_absolute_name(value))

    def process(self, node: cst.CSTNode) -> object:
        """Process a node

        :param node: A node to process
        :type node: :py:class:`libcst.CSTNode`
        :return: A python object corresponding to the ``node`` type. Any unsupported types are replaced with a
            :py:class:`.Python` instance
        """
        return self._process_node(node)

    def __call__(self, node: cst.CSTNode):
        return self.process(node)


class Disambiguator:
    """Class that processes an object by replacing :py:class:`str` with a subclass of :py:class:`.StringTag`

    To determine whether the string should be a :py:class:`.Python` or a :py:class:`.String` object uses a list of
    names in the namespace

    If :py:property:`replace_lists_with_tuples` is set to True Disambiguator replaces lists with tuples
    """

    def __init__(self):
        self.names: tp.List[str] = []
        self.replace_lists_with_tuples: bool = False

    def add_name(self, name: str):
        """Add a name to the list of names in a namespace

        :param name: Name to add
        :type name: str
        :return: None
        """
        self.names.append(name)

    def _process_dict(self, obj: dict) -> dict:
        result = OrderedDict()
        for key in obj:
            result[self._process(key)] = self._process(obj[key])
        return dict(result)

    def _process_list(self, obj: list) -> tp.Union[list, tuple]:
        result = []
        for element in obj:
            result.append(self._process(element))
        if self.replace_lists_with_tuples:
            return tuple(result)
        return result

    def _process(self, obj: tp.Any) -> tp.Any:
        if isinstance(obj, dict):
            return self._process_dict(obj)
        if isinstance(obj, list):
            return self._process_list(obj)
        if isinstance(obj, str):
            return Python(obj) if is_correct(self.names, obj) else String(obj)
        return obj

    def __call__(self, node: tp.Any):
        return self._process(node)


def is_correct(names: tp.List[str], code: str) -> bool:
    """Check code for correctness if names are available in the namespace.

    :param names: Namespace in which the correctness is asserted
    :type names: list[str]
    :param code: String to check for correctness
    :type code: str
    :return: Whether code is a correct python code
    :rtype: bool
    """
    code_string = "\n".join([*(f"import {name}\n{name}" for name in names), code])
    with open(devnull, "w", encoding="utf-8") as null:
        return check(code_string, "", Reporter(null, null)) == 0
