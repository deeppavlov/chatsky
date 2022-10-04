"""This module contains functions for converting a script to a :py:mod:`.networkx`
"""
import typing as tp
from copy import copy

from df_script_parser.utils.code_wrappers import StringTag, Python, String
from df_script_parser.utils.namespaces import Call, Request
from df_script_parser.utils.validators import keywords_dict
from df_script_parser.utils.exceptions import ScriptValidationError, ResolutionError

if tp.TYPE_CHECKING:
    from df_script_parser.processors.recursive_parser import RecursiveParser


def get_destination(label: StringTag, resolve_name: tp.Callable):
    if isinstance(label, Python):
        resolved_value = resolve_name(label)
        if resolved_value is None:
            raise RuntimeError(f"Resolved value is none: {label.__dict__}")
        if isinstance(resolved_value, Python):
            parsed_value = resolved_value.metadata.get("parsed_value")
            if parsed_value is None:
                raise RuntimeError(f"Parsed value is none: {label.__dict__}")
            if isinstance(parsed_value, tuple):
                flow = parsed_value[0]
                node = parsed_value[1]
                if isinstance(flow, Python):
                    flow = resolve_name(flow)
                if isinstance(node, Python):
                    node = resolve_name(node)
                if isinstance(flow, String) and isinstance(node, String):
                    return flow.display_value, node.display_value
    return ("NONE",)


def script2graph(
    traversed_path: tp.List[StringTag],
    final_value: tp.Union[StringTag, Call],
    paths: tp.List[tp.List[str]],
    project: "RecursiveParser",
):
    if len(traversed_path) == 0:
        raise ScriptValidationError(f"traversed_path is empty: {traversed_path, final_value, paths}")

    if project.resolve_name(traversed_path[0]) in keywords_dict["GLOBAL"]:
        node_name: tp.Union[tp.Tuple[str], tp.Tuple[str, str]] = ("GLOBAL",)
    else:
        node_name = (
            project.resolve_name(traversed_path[0]).absolute_value,
            project.resolve_name(traversed_path[1]).absolute_value,
        )

    project.graph.add_node(
        node_name,
        ref=copy(paths[len(node_name)]),
        local=project.resolve_name(traversed_path[1]) in keywords_dict["LOCAL"],
    )

    if project.resolve_name(traversed_path[len(node_name)]) in keywords_dict["TRANSITIONS"]:
        if not isinstance(project.resolve_name(final_value), StringTag):
            raise ScriptValidationError(
                f"Condition is not a ``StringTag: {final_value}. traversed_path={traversed_path}"
            )
        try:
            label, label_ref = project.get_requested_object(
                Request.from_str(traversed_path[len(node_name) + 1].absolute_value)
            )
        except ResolutionError:
            label, label_ref = traversed_path[len(node_name) + 1], copy(paths[len(node_name) + 1])
        destination = get_destination(traversed_path[len(node_name) + 1], project.resolve_name)
        project.graph.add_edge(
            node_name,
            destination,
            label_ref=label_ref,
            label=label.display_value,
            condition_ref=copy(paths[len(node_name) + 2]),
            condition=project.resolve_name(final_value).display_value,
        )
