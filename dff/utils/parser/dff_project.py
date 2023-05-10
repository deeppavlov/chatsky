"""
DFF Project
-----------
This module defines a class that represents a DFF project --
a collection of python source files that define a script and a Pipeline.

Glossary
^^^^^^^^
Script Initializer -- A function that takes a DFF script and uses it to initialize an object to store and process it.
"""
from pathlib import Path
import json
import typing as tp
import logging
from collections import defaultdict
import ast
import inspect
from typing_extensions import TypeAlias

try:
    import networkx as nx
except ImportError:
    raise ImportError("Module `networkx` is not installed. Install it with `pip install dff[parser]`.")

from dff.utils.parser.parser_objects import (
    BaseParserObject,
    Call,
    ReferenceObject,
    Import,
    ImportFrom,
    Assignment,
    Expression,
    Dict,
    String,
    Iterable,
    Statement,
    Python,
)
from dff.utils.parser.utils import cached_property
from dff.utils.parser.namespace import Namespace
from dff.utils.parser.exceptions import ScriptValidationError, ParsingError
from dff.utils.parser.yaml import yaml
from dff.pipeline.pipeline.pipeline import Actor, Pipeline
from dff.script.core.keywords import Keywords
import dff.script.labels as labels

logger = logging.getLogger(__name__)

script_initializers: tp.Dict[str, inspect.Signature] = {
    **{
        actor_name: inspect.signature(Actor.__init__)
        for actor_name in (
            "dff.pipeline.pipeline.actor.Actor",
            "dff.pipeline.pipeline.pipeline.Actor",
        )
    },
    **{
        pipeline_name: inspect.signature(Pipeline.from_script)
        for pipeline_name in (
            "dff.pipeline.Pipeline.from_script",
            "dff.pipeline.pipeline.pipeline.Pipeline.from_script",
        )
    },
}
"""
A mapping from names of script initializers to their signatures.

:meta hide-value:
"""

label_prefixes = (
    "dff.script.labels.std_labels.",
    "dff.script.labels.",
)
"""A tuple of possible prefixes for label names."""

label_args: tp.Dict[str, inspect.Signature] = {
    label_prefix + label.__name__: inspect.signature(label)
    for label in (
        getattr(labels, lbl)
        for lbl in (
            "backward",
            "forward",
            "previous",
            "repeat",
            "to_fallback",
            "to_start",
        )
    )
    for label_prefix in label_prefixes
}
"""
A mapping from label names to their signatures.

:meta hide-value:
"""

keyword_prefixes = (
    "dff.script.core.keywords.Keywords.",
    "dff.script.core.keywords.",
    "dff.script.",
    "dff.script.Keywords.",
)
"""A tuple of possible keyword name prefixes."""

keyword_dict = {k: [keyword_prefix + k for keyword_prefix in keyword_prefixes] for k in Keywords.__members__}
"""
A mapping from short names of keywords to all their full names.
(e.g. GLOBAL -> [dff.script.GLOBAL, dff.script.Keywords.GLOBAL, ...])

:meta hide-value:
"""

keyword_list = [keyword_prefix + k for keyword_prefix in keyword_prefixes for k in Keywords.__members__]
"""
A list of all keyword full names.

:meta hide-value:
"""

reversed_keyword_dict = {keyword_prefix + k: k for k in Keywords.__members__ for keyword_prefix in keyword_prefixes}
"""
A mapping from full keyword names to their short names.

:meta hide-value:
"""

RecursiveDictValue: TypeAlias = tp.Union[str, tp.Dict[str, "RecursiveDictValue"]]
RecursiveDict: TypeAlias = tp.Dict[str, "RecursiveDictValue"]
DFFProjectDict: TypeAlias = tp.Dict[str, "RecursiveDict"]


class DFFProject(BaseParserObject):
    """
    A collection of files that define a script and a script initializer.
    """

    def __init__(
        self,
        namespaces: tp.List["Namespace"],
        validate: bool = True,
        script_initializer: tp.Optional[str] = None,
    ):
        """

        :param namespaces: A list of Namespaces that comprise a DFF project.
        :param validate:
            Whether to perform validation -- check for a script initializer and validate its arguments.
            Defaults to True.
        :param script_initializer:
            A colon-separated string that points to a script initializer call.
            The first part of the string should be the name of the namespace.
            The second part of the string should be the name of the object that is a result of script initializer call.
            Defaults to None.
        """
        BaseParserObject.__init__(self)
        self.children: tp.MutableMapping[str, Namespace] = {}
        self.script_initializer = script_initializer
        """
        A colon-separated string that points to a script initializer call.
        The first part of the string should be the name of the namespace.
        The second part of the string should be the name of the object that is a result of script initializer call.
        """
        if script_initializer is not None and len(script_initializer.split(":")) != 2:
            raise ValueError(
                f"`script_initializer` should be a string of two parts separated by `:`: {script_initializer}"
            )
        for namespace in namespaces:
            self.add_child(namespace, namespace.name)
        if validate:
            _ = self.graph

    def get_namespace(self, namespace_name: str) -> tp.Optional[Namespace]:
        """Get a namespace by its name. Return None if it does not exist."""
        return self.children.get(namespace_name) or self.children.get(namespace_name + ".__init__")

    @cached_property
    def script_initializer_call(self) -> Call:
        """
        Return a Script Initializer call.
        If `self.script_initializer` is specified during `__init__` return the call it points to and verify it.
        Otherwise, search for a Script Initializer call in `self.namespaces`.

        :raises ScriptValidationError:
            This exception is called under these conditions:

            - If `self.script_initializer` is specified during `__init__` and any of the following is true:
                - Namespace specified by the first part of the `script_initializer`
                  does not exist in `self.namespaces`.
                - Object specified by the second part of the `script_initializer` does not exist in namespace.
                - Object specified by the second part of the `script_initializer` is not an assignment.
                - Object specified by the second part of the `script_initializer`
                  assigns an object other than :py:class:`~.Call`.
                - Object specified by the second part of the `script_initializer`
                  assigns an object other than any specified in :py:data:`~.script_initializers`.
            - If `self.script_initializer` is not specified and a search found multiple or no Script Initializer calls.
        """
        call = None
        if self.script_initializer is not None:
            namespace_name, obj_name = self.script_initializer.split(":")
            namespace = self.children.get(namespace_name)
            if namespace is None:
                raise ScriptValidationError(f"Namespace {namespace_name} not found.")
            obj = namespace.children.get(obj_name)
            if obj is None:
                raise ScriptValidationError(f"Object {obj_name} not found in namespace {namespace_name}.")
            if not isinstance(obj, Assignment):
                raise ScriptValidationError(f"Object {obj_name} is not `Assignment`: {obj}")
            value = obj.children["value"]
            if not isinstance(value, Call):
                raise ScriptValidationError(f"Object {obj_name} is not `Call`: {value}")
            if value.func_name not in script_initializers.keys():
                raise ScriptValidationError(f"Object {obj_name} is not a Script Initializer: {value.func_name}")
            return value
        for namespace in self.children.values():
            for statement in namespace.children.values():
                if isinstance(statement, Assignment):
                    value = statement.children["value"]
                    if isinstance(value, Call):
                        func_name = value.func_name
                        if func_name in script_initializers.keys():
                            if call is None:
                                call = value
                            else:
                                raise ScriptValidationError(
                                    f"Found two Script Initializer calls\nFirst: {str(call)}\nSecond:{str(value)}"
                                )
        if call is not None:
            return call
        raise ScriptValidationError(
            "Script Initialization call is not found (use either `Actor` or `Pipeline.from_script`"
        )

    @cached_property
    def script_initializer_dependencies(self) -> tp.Dict[str, tp.Set[str]]:
        """Dependencies of script initializer."""
        return self.script_initializer_call.dependencies()

    @cached_property
    def script(self) -> tp.Tuple[Expression, Expression, Expression]:
        """
        Extract objects representing script, start label and fallback label from Script Initializer call.
        If fallback label is not specified in that call, return start label instead.

        :raises ScriptValidationError:
            If Script Initializer call does not include `script` or `start_label` parameters.
        """
        call = self.script_initializer_call
        args: tp.Dict[str, Expression] = call.get_args(script_initializers[call.func_name])
        script = args.get("script")
        start_label = args.get("start_label")
        fallback_label = args.get("fallback_label")

        # script validation
        if script is None or script == "None":
            raise ScriptValidationError(f"Actor argument `script` is not found: {str(call)}")

        # start_label validation
        if start_label is None or start_label == "None":
            raise ScriptValidationError(f"Actor argument `start_label` is not found: {str(call)}")

        # fallback_label validation
        if fallback_label is None or fallback_label == "None":
            fallback_label = start_label

        return script, start_label, fallback_label

    @cached_property
    def resolved_script(
        self,
    ) -> tp.Tuple[
        tp.Dict[Expression, tp.Dict[tp.Optional[Expression], tp.Dict[str, Expression]]],
        tp.Tuple[str, str],
        tp.Tuple[str, str],
    ]:
        """
        Resolve values of :py:attr:`.~DFFProject.script`.
        The first value (script) is resolved in the following way:

        1. For each (`flow_name`, `flow`) pair in the script resulting dict has a
        (`resolved_flow_name`, `resolved_flow`) pair where `resolved_flow_name` is the result of
        :py:meth:`~.ReferenceObject.resolve_expression` applied to `flow_name`;
        and `resolved_flow` is a dictionary constructed in the following way:

        2. If `resolved_flow_name` is `GLOBAL`, `resolved_flow` is a dictionary with a single pair
        (`None`, `resolved_node`) where `resolved_node` is the result of processing `flow` in the same way nodes are
        processed (see step 3).
        If `resolved_flow_name` is not `GLOBAL`, for each (`node_name`, `node`) pair in `flow`
        resulting dict `resolved_flow` contains a pair (`resolved_node_name`, `resolved_node`) where
        `resolved_node_name` is the result of :py:meth:`~.ReferenceObject.resolve_expression` applied to `node_name`;
        and `resolved_node` is a dictionary constructed in the following way:

        3. For each (`key`, `value`) pair in `node` resulting dict has a
        (`keyword`, `resolved_value`) pair where `resolved_value` is the result of
        :py:meth:`~.ReferenceObject.resolve_expression` applied to `value`; and `keyword` is one of the keys of
        :py:data:`~.keyword_dict`. If `key` is not a keyword, :py:exc:`~.ScriptValidationError`
        is raised. Additionally the result contains a (__node__, `resolved_node`) pair
        where __node__ is a literal string and `resolved_node` is the result of
        :py:meth:`~.ReferenceObject.resolve_expression` applied to `node`.

        The second and third values (start label and fallback label) are resolved in the following way:

        If a label resolves to :py:class:`~.Iterable` of length 2 both elements of which resolve to
        :py:class:`~.String` a tuple of their values is returned. Otherwise, :py:exc:`~.ScriptValidationError`
        is raised.

        Labels are also validated (checking that label keys exist in the script).

        :return: A tuple (resolved_script, resolved_start_label, resolved_fallback_label).
        :raises ScriptValidationError:
            During script resolution if:
                - The first element of :py:attr:`~.DFFProject.script` does not resolve to :py:class:`~.Dict`.
                - If `resolved_flow_name` is not `GLOBAL` and `flow` does not resolve to :py:class:`~.Dict`.
                - Here `node` refers to both `node` and, if `resolved_flow_name` is `GLOBAL`, `flow`:

                  - If `node` does not resolve to :py:class:`~. Dict`.
                  - If any key in `node` is not a keyword (is not in :py:data:`~.keyword_list`).
                  - If any key in `node` is a `GLOBAL` or `LOCAL` keyword.
                  - If any key is found twice inside the `node` dictionary.

            During label resolution if:
                - Label does not resolve to :py:class:`~.Iterable`.
                - Number of elements in label is not 2.
                - Label elements do not resolve to :py:class:`~.String`.

            During label validation if a node referenced by a label does not exist in resolved script.
        """
        script: tp.DefaultDict[Expression, tp.Dict[tp.Optional[Expression], tp.Dict[str, Expression]]] = defaultdict(
            dict
        )

        def resolve_label(label: Expression) -> tp.Tuple[str, str]:
            label = ReferenceObject.resolve_expression(label)
            if not isinstance(label, Iterable):
                raise ScriptValidationError(f"Label {label} is not iterable.")
            if len(label) != 2:
                raise ScriptValidationError(f"Length of label should be 2: {label}")
            resolved_flow_name = ReferenceObject.resolve_absolute(label[0])
            resolved_node_name = ReferenceObject.resolve_absolute(label[1])
            if not isinstance(resolved_flow_name, String) or not isinstance(resolved_node_name, String):
                raise ScriptValidationError(f"Label elements should be strings: {label}")
            return str(resolved_flow_name), str(resolved_node_name)

        def resolve_node(node_info: Expression) -> tp.Dict[str, Expression]:
            result: tp.Dict[str, Expression] = {}
            node_info = ReferenceObject.resolve_expression(node_info)
            if not isinstance(node_info, Dict):
                raise ScriptValidationError(f"Node {str(node_info)} is not a Dict")
            result["__node__"] = node_info
            for key, value in node_info.items():
                str_key = key.true_value()
                if str_key not in keyword_list:
                    raise ScriptValidationError(f"Node key {str_key} is not a keyword")
                if str_key in keyword_dict["GLOBAL"]:
                    raise ScriptValidationError(f"Node key is a GLOBAL keyword: {str_key}")
                if str_key in keyword_dict["LOCAL"]:
                    raise ScriptValidationError(f"Node key is a LOCAL keyword: {str_key}")

                keyword = reversed_keyword_dict[str_key]

                if result.get(keyword) is not None:  # duplicate found
                    raise ScriptValidationError(f"Keyword {str_key} is used twice in one node: {str(node_info)}")

                result[keyword] = ReferenceObject.resolve_expression(value)
            return result

        flows = ReferenceObject.resolve_absolute(self.script[0])
        if not isinstance(flows, Dict):
            raise ScriptValidationError(f"{str(self.script[0])} is not a Dict: {str(flows)}")
        for flow, nodes in flows.items():
            resolved_flow = ReferenceObject.resolve_expression(flow)
            if flow in keyword_dict["GLOBAL"]:
                script[resolved_flow][None] = resolve_node(nodes)
            else:
                resolved_nodes = ReferenceObject.resolve_expression(nodes)
                if not isinstance(resolved_nodes, Dict):
                    raise ScriptValidationError(f"{str(nodes)} is not a Dict: {str(resolved_nodes)}")
                for node, info in resolved_nodes.items():
                    script[resolved_flow][ReferenceObject.resolve_expression(node)] = resolve_node(info)

        resolved_start_label = resolve_label(self.script[1])
        resolved_fallback_label = resolve_label(self.script[2])

        # validate labels
        for resolved_label in (resolved_start_label, resolved_fallback_label):
            flow = script.get(resolved_label[0])  # type: ignore
            if flow is None:
                raise ScriptValidationError(
                    f"Not found flow {str(resolved_label[0])} in {[str(key) for key in script.keys()]}"
                )
            else:
                if flow.get(resolved_label[1]) is None:  # type: ignore
                    raise ScriptValidationError(
                        f"Not found node {str(resolved_label[1])} in {[str(key) for key in script.keys()]}"
                    )

        return script, resolved_start_label, resolved_fallback_label

    @cached_property
    def graph(self) -> nx.MultiDiGraph:
        """
        Export DFF project as a networkx graph and validate transitions.

        Resulting graph contains the following fields:
            - full_script: Stores dictionary exported via :py:meth:`~.DFFProject.to_dict`.
            - start_label: A tuple of two strings (second element of :py:attr:`~.DFFProject.resolved_script`).
            - fallback_label: A tuple of two strings (third element of :py:attr:`~.DFFProject.resolved_script`).

        All nodes of the resulting graph are represented by a single value -- a tuple of strings or lists of strings.

        For each node in the script there is a node in the resulting graph which has a value of:
            - `("GLOBAL_NODE", flow_name)` if the node belongs to the `GLOBAL` flow.
            - `("LOCAL_NODE", flow_name, node_name)` if the node is a `LOCAL` node.
            - `("NODE", flow_name, node_name)` otherwise.

        where `flow_name` and `node_name` are results of `str` applied to `resolved_flow_name` and `resolved_node_name`
        respectively (see documentation of :py:attr:`~.DFFProject.resolved_script`).

        Additionally, nodes representing script nodes contain the following field:
            - ref: Path to the :py:class:`~.Expression` representing the node (see :py:attr:`~.BaseParserObject.path`).

        Graph has other nodes:
            - `("NONE",)` -- empty node.
            - Label nodes. The first element of their value is `"LABEL"`,
              the second element is the name of the label used (e.g. `"to_fallback"`).
              The rest of the elements are tuples of two strings with the first element being a name
              of a function argument, and the second element being its `true_value`.

        For each transition between script nodes there is an edge in the graph:
        The first node of the edge is always a node representing a node in the script.
        The second node is either a node in the script (if transition directly specifies it), a label node
        (if one of the labels from :py:mod:`~.dff.script.labels` is used) and an empty node otherwise.

        All edges have 4 fields:
            - label_ref: Path to the object defining transition label.
            - label: `str` of either absolute value of the label or the label itself.
            - condition_ref: Path to the object defining transition condition.
            - condition: `str` of either absolute value of the condition or the condition itself.

        :raises ScriptValidationError:
            - If `TRANSITION` keyword does not refer to a :py:class:`~.Dict`.
            - If any of the first two elements of any transition label is not :py:class:`~.String`.
        """

        def resolve_label(label: Expression, current_flow: Expression) -> tuple:
            if isinstance(label, ReferenceObject):  # label did not resolve (possibly due to a missing func def)
                return ("NONE",)
            if isinstance(label, String):
                return "NODE", str(current_flow), str(label)
            if isinstance(label, Iterable):
                resolved_flow_name = ReferenceObject.resolve_absolute(label[0])
                resolved_node_name = ReferenceObject.resolve_absolute(label[1])
                if not isinstance(resolved_flow_name, String):
                    raise ScriptValidationError(f"First argument of label is not str: {label}")
                if len(label) == 2 and not isinstance(resolved_node_name, String):  # second element is priority
                    return "NODE", str(current_flow), str(resolved_flow_name)
                if len(label) == 2:
                    return "NODE", str(resolved_flow_name), str(resolved_node_name)
                if len(label) == 3:
                    if not isinstance(resolved_node_name, String):
                        raise ScriptValidationError(f"Second argument of label is not str: {label}")
                    return "NODE", str(resolved_flow_name), str(resolved_node_name)
            if isinstance(label, Call):
                if label.func_name in label_args:
                    return (
                        "LABEL",
                        label.func_name.rpartition(".")[2],
                        *[
                            (key, value.true_value())
                            for key, value in label.get_args(label_args[label.func_name]).items()
                        ],
                    )
            logger.warning(f"Label did not resolve: {label}")
            return ("NONE",)

        graph = nx.MultiDiGraph(
            full_script=self.to_dict(),
            start_label=self.resolved_script[1],
            fallback_label=self.resolved_script[2],
        )
        for flow_name, flow in self.resolved_script[0].items():
            for node_name, node_info in flow.items():
                if node_name is None:
                    current_label = ("GLOBAL_NODE", str(flow_name))
                elif node_name in keyword_dict["LOCAL"]:
                    current_label = ("LOCAL_NODE", str(flow_name), str(node_name))
                else:
                    current_label = ("NODE", str(flow_name), str(node_name))

                graph.add_node(
                    current_label,
                    ref=node_info["__node__"].path,
                )
                transitions = node_info.get("TRANSITIONS")
                if transitions is None:
                    continue
                if not isinstance(transitions, Dict):
                    raise ScriptValidationError(f"TRANSITIONS keyword should point to a dictionary: {transitions}")
                for transition_label, transition_condition in transitions.items():
                    graph.add_edge(
                        current_label,
                        resolve_label(ReferenceObject.resolve_expression(transition_label), flow_name),
                        label_ref=ReferenceObject.resolve_absolute(transition_label).path,
                        label=str(ReferenceObject.resolve_absolute(transition_label)),
                        condition_ref=ReferenceObject.resolve_absolute(transition_condition).path,
                        condition=str(ReferenceObject.resolve_absolute(transition_condition)),
                    )
        return graph

    def to_dict(
        self,
        object_filter: tp.Optional[tp.Dict[str, tp.Set[str]]] = None,
    ) -> DFFProjectDict:
        """
        Export DFF Project as a dictionary.

        First-level keys in the dictionary are the names of the namespaces in the project.
        Second-level keys in the dictionary are the names of the objects in the namespaces.

        Values in the dictionary are results of applying the `process` function to the objects
        in the namespaces. The function works in the following way:

        - If the object is :py:class:`~.Assignment`, the result is the same as the one that
          assignment value would have.

          `process(target=value) = process(value)`
        - If the object is :py:class:`~.Import` or :py:class:`~.ImportFrom`, the result is the string
          representation of the object without import alias.

          `process(import a as b) = process(import a) = "import a"`
        - If the object is :py:class:`~.Dict`, the result is also a dictionary in which keys and values are results
          of applying the `process` function to keys and values of the dictionary being processed.

          `process({a: b}) = {process(a): process(b)}`
        - Otherwise, the result is the string representation of the object (:py:meth:`~.BaseParserObject.__str__`).

          `process(a) = str(a)`

        :param object_filter:
            A dictionary from namespace names to sets of object names.
            Only objects in the sets will be in the resulting dictionary.
            Defaults to :py:attr:`~.DFFProject.script_initializer_dependencies`.
        :raises ScriptValidationError:
            Inside the `process` function -- if a key of :py:class:`~.Dict` is also a `dict`.
        :raises TypeError:
            Inside the `process` function -- if value is not a :py:class:`~.Statement` nor a :py:class:`~.Expression`.
        """

        def process_base_parser_object(bpo: BaseParserObject) -> RecursiveDictValue:
            if isinstance(bpo, Assignment):
                return process_base_parser_object(bpo.children["value"])
            if isinstance(bpo, Import):
                return f"import {bpo.module}"
            if isinstance(bpo, ImportFrom):
                return f"from {bpo.level * '.' + bpo.module} import {bpo.obj}"
            if isinstance(bpo, Dict):
                processed_dict: RecursiveDict = {}
                for key, value in bpo.items():
                    processed_key = process_base_parser_object(key)
                    if not isinstance(processed_key, str):
                        raise ScriptValidationError(f"Key should be `str`: {processed_key}")
                    processed_dict[processed_key] = process_base_parser_object(value)
                return processed_dict
            elif isinstance(bpo, (Statement, Expression)):
                return str(bpo)
            raise TypeError(str(type(bpo)) + "_" + repr(bpo))

        result: DFFProjectDict = defaultdict(dict)
        if object_filter is None:
            object_filter = self.script_initializer_dependencies

        for namespace_name, namespace in self.children.items():
            namespace_filter = object_filter.get(namespace_name)
            if namespace_filter is not None:
                for obj_name, obj in namespace.children.items():
                    if obj_name in namespace_filter:
                        result[namespace_name][obj_name] = process_base_parser_object(obj)
        return dict(result)

    @classmethod
    def from_dict(
        cls,
        dictionary: DFFProjectDict,
        validate: bool = True,
        script_initializer: tp.Optional[str] = None,
    ):
        """
        Construct DFF Project from a dictionary.

        :param dictionary:
            A dictionary with the same characteristics as one returned by :py:meth:`~.DFFProject.to_dict`.
        :param validate:
            Whether to perform validation -- check for a script initializer and validate its arguments.
            Defaults to True.
        :param script_initializer:
            A colon-separated string that points to a script initializer call.
            The first part of the string should be the name of the namespace.
            The second part of the string should be the name of the object that is a result of script initializer call.
            Defaults to None.

        :raises ParsingError:
            - If a dictionary object is an Import statement that contains an import alias.
            - If a dictionary object is an Assignment statement.
        """

        def process_dict(d):
            return (
                "{" + ", ".join([f"{k}: {process_dict(v) if isinstance(v, dict) else v}" for k, v in d.items()]) + "}"
            )

        namespaces = []
        for namespace_name, namespace in dictionary.items():
            objects = []
            for obj_name, obj in namespace.items():
                if isinstance(obj, str):
                    split = obj.split(" ")
                    if split[0] == "import":
                        if len(split) != 2:
                            raise ParsingError(
                                f"Import statement should contain 2 words. AsName is set via key.\n{obj}"
                            )
                        objects.append(obj if split[1] == obj_name else obj + " as " + obj_name)
                    elif split[0] == "from":
                        if len(split) != 4:
                            raise ParsingError(
                                f"ImportFrom statement should contain 4 words. AsName is set via key.\n{obj}"
                            )
                        objects.append(obj if split[3] == obj_name else obj + " as " + obj_name)
                    elif obj_name.isnumeric():
                        objects.append(obj)  # unsupported by BPOs statement (e.g. func def)
                    else:
                        if isinstance(ast.parse(obj).body[0], (ast.Assign, ast.AnnAssign)):
                            raise ParsingError(f"Assignment statement should not be used in the dictionary: {obj}")
                        objects.append(f"{obj_name} = {obj}")
                else:
                    objects.append(f"{obj_name} = {str(process_dict(obj))}")
            namespaces.append(Namespace.from_ast(ast.parse("\n".join(objects)), location=namespace_name.split(".")))
        return cls(namespaces, validate, script_initializer)

    def __getitem__(self, item: str) -> Namespace:
        if isinstance(item, str):
            return self.children[item]
        raise TypeError(f"{type(item)}")

    @cached_property
    def path(self) -> tp.Tuple[str, ...]:
        return ()

    @cached_property
    def namespace(self) -> "Namespace":
        raise RuntimeError(f"DFFProject does not have a `namespace` attribute\n{repr(self)}")

    @cached_property
    def dff_project(self) -> "DFFProject":
        return self

    def dump(self, current_indent=0, indent=4) -> str:
        return repr(self.children)

    @classmethod
    def from_ast(cls, node, **kwargs):
        raise NotImplementedError()

    @classmethod
    def from_python(
        cls,
        project_root_dir: Path,
        entry_point: Path,
        validate: bool = True,
        script_initializer: tp.Optional[str] = None,
    ):
        """
        Construct DFF Project from a directory of python files.

        Namespaces are created from files using :py:meth:`~.Namespace.from_file`.

        :param project_root_dir:
            A directory that stores the project.
        :param entry_point:
            A file to start processing with (only files that are imported in processed files will be processed).
        :param validate:
            Whether to perform validation -- check for a script initializer and validate its arguments.
            Defaults to True.
        :param script_initializer:
            A colon-separated string that points to a script initializer call.
            The first part of the string should be the name of the namespace.
            The second part of the string should be the name of the object that is a result of script initializer call.
            Instead of a colon-separated string a name of the object can be provided
            in which case the name of the namespace is assumed to be the name of `entry_point`.
            Defaults to None.
        """
        namespaces = {}
        if not project_root_dir.exists():
            raise RuntimeError(f"Path does not exist: {project_root_dir}")
        if not entry_point.exists():
            raise RuntimeError(f"File {entry_point} does not exist in {project_root_dir}")

        def _process_file(file: Path):
            namespace = Namespace.from_file(project_root_dir, file)
            namespaces[namespace.name] = namespace
            result = namespace.name

            for imported_file in namespace.get_imports():
                if imported_file not in namespaces.keys():
                    path = project_root_dir.joinpath(*imported_file.split(".")).with_suffix(".py")
                    if path.exists():
                        _process_file(path)
            return result

        namespace_name = _process_file(entry_point)

        if script_initializer is not None:
            if not isinstance(script_initializer, str):
                raise TypeError("Argument `script_initializer` should be `str`")
            if ":" not in script_initializer:
                script_initializer = namespace_name + ":" + script_initializer

        return cls(list(namespaces.values()), validate, script_initializer)

    def to_python(self, project_root_dir: Path, object_filter: tp.Optional[tp.Dict[str, tp.Set[str]]] = None):
        """
        Export DFF Project as a directory of python files.

        For each namespace in the project if a file corresponding to that namespace does not exist in the directory,
        a new file will be created and the namespace will be dumped into it.
        If a file already exists, it will be edited in the following way:

        All statements are extracted from the file the same way :py:meth:`~.Namespace.from_file` extracts them.

        Extracted statements are then edited:
        Starting from the top of the namespace its statements are inserted into the list of extracted statements
        as late as possible (always inserts before the last inserted statement and if a statement with the same name
        already exists it will be replaced; if a statement with the same name already exists but comes after the last
        inserted statement a warning is given and a new statement is inserted before the last inserted statement
        resulting in two statements with the same name -- one before the last inserted statement and one after).

        This is done with the following in mind:
        If two statements come in the namespace one after another, their order likely matters (either because of direct
        referencing or some actions done in the first statement that affect the result of the second statement).

        :param project_root_dir:
            A directory to extract the project to.
        :param object_filter:
            An optional dictionary from namespace names to sets of object names. Only objects specified in the filter
            will be written into files.
            Defaults to :py:attr:`~.DFFProject.script_initializer_dependencies`.
        """
        logger.info(f"Executing `to_python` with project_root_dir={project_root_dir}")
        if object_filter is None:
            object_filter = self.script_initializer_dependencies

        for namespace in self.children.values():
            namespace_object_filter = object_filter.get(namespace.name)

            if namespace_object_filter is None:
                continue

            file = project_root_dir.joinpath(*namespace.name.split(".")).with_suffix(".py")
            if file.exists():
                objects: tp.List[Statement] = []
                names: tp.Dict[str, int] = {}  # reverse index of names

                with open(file, "r", encoding="utf-8") as fd:
                    parsed_file = ast.parse(fd.read())
                for statement in parsed_file.body:
                    statements = Statement.auto(statement)
                    if isinstance(statements, dict):
                        for obj_name, obj in statements.items():
                            if names.get(obj_name) is not None:
                                logger.warning(
                                    f"The same name is used twice:\n{str(names.get(obj_name))}\n{str(obj)}\nfile:{file}"
                                )
                            names[obj_name] = len(objects)
                            objects.append(obj)
                    elif isinstance(statements, Python):
                        objects.append(statements)
                    else:
                        raise RuntimeError(statement)

                last_insertion_index = len(objects)
                for replaced_obj_name, replaced_obj in reversed(list(namespace.children.items())):
                    if replaced_obj_name in namespace_object_filter:
                        obj_index = names.get(replaced_obj_name)
                        if obj_index is not None:
                            if obj_index > last_insertion_index:
                                logger.warning(
                                    f"Object order was changed. This might cause issues.\n"
                                    f"Inserting object: {str(replaced_obj)}\n"
                                    f"New script places it below: {str(objects[last_insertion_index])}"
                                )
                                objects.insert(last_insertion_index, replaced_obj)
                            else:
                                objects.pop(obj_index)
                                objects.insert(obj_index, replaced_obj)
                                last_insertion_index = obj_index
                        else:
                            objects.insert(last_insertion_index, replaced_obj)

                with open(file, "w", encoding="utf-8") as fd:
                    fd.write(Namespace.dump_statements(objects))
            else:
                logger.warning(f"File {file} is not found. It will be created.")
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
                with open(file, "w", encoding="utf-8") as fd:
                    fd.write(namespace.dump(object_filter=namespace_object_filter))

    @classmethod
    def from_yaml(cls, file: Path, validate: bool = True, script_initializer: tp.Optional[str] = None):
        """
        Construct DFF Project from a yaml file.

        :param file:
            Yaml file containing a result of :py:meth:`~.DFFProject.to_yaml`.
        :param validate:
            Whether to perform validation -- check for a script initializer and validate its arguments.
            Defaults to True.
        :param script_initializer:
            A colon-separated string that points to a script initializer call.
            The first part of the string should be the name of the namespace.
            The second part of the string should be the name of the object that is a result of script initializer call.
            Defaults to None.
        """
        with open(file, "r", encoding="utf-8") as fd:
            return cls.from_dict(yaml.load(fd), validate, script_initializer)

    def to_yaml(self, file: Path):
        """
        Export DFF Project in the yaml format.
        Uses :py:meth:`~.DFFProject.to_dict`.
        """
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()
        with open(file, "w", encoding="utf-8") as fd:
            yaml.dump(self.to_dict(), fd)

    @classmethod
    def from_graph(cls, file: Path, validate: bool = True, script_initializer: tp.Optional[str] = None):
        """
        Construct DFF Project from a graph file.

        :param file:
            Graph file containing a result of :py:meth:`~.DFFProject.to_graph`.
        :param validate:
            Whether to perform validation -- check for a script initializer and validate its arguments.
            Defaults to True.
        :param script_initializer:
            A colon-separated string that points to a script initializer call.
            The first part of the string should be the name of the namespace.
            The second part of the string should be the name of the object that is a result of script initializer call.
            Defaults to None.
        """
        with open(file, "r", encoding="utf-8") as fd:
            return cls.from_dict(json.load(fd)["graph"]["full_script"], validate, script_initializer)

    def to_graph(self, file: Path):
        """
        Export DFF Project in the graph format.
        Graph file contains :py:attr:`~.DFFProject.graph` exported by :py:func:`networkx.readwrite.node_link_data`.
        """
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()
        with open(file, "w", encoding="utf-8") as fd:
            json.dump(nx.readwrite.node_link_data(self.graph), fd, indent=4)
