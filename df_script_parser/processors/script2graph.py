"""This module contains functions for converting a script to a :py:mod:`.networkx`
"""
import typing as tp
from copy import copy

import networkx as nx  # type: ignore

from df_script_parser.utils.code_wrappers import StringTag, Python, String
from df_script_parser.utils.namespaces import Call
from df_script_parser.utils.validators import keywords_dict
from df_script_parser.utils.exceptions import ScriptValidationError


def script2graph(
    traversed_path: tp.List[StringTag],
    final_value: tp.Union[StringTag, Call],
    paths: tp.List[tp.List[str]],
    graph: nx.MultiDiGraph,
    resolve_name: tp.Callable, # TODO: unused
):
    def get_destination(label: StringTag): # TODO: move outside of script2graph
        if isinstance(label, Python):
            resolved_value = label.metadata.get("resolved_value")
            if resolved_value is None:
                raise RuntimeError(f"Resolved value is none: {label.__dict__}")
            if isinstance(resolved_value, Python):
                parsed_value = resolved_value.metadata.get("parsed_value")
                if parsed_value is None:
                    raise RuntimeError(f"Parsed value is none: {label.__dict__}")
                if isinstance(parsed_value, tuple):
                    if isinstance(parsed_value[0], String) and isinstance(parsed_value[1], String):
                        return parsed_value[0].display_value, parsed_value[1].display_value
        return None # TODO: useless

    if len(traversed_path) == 0:
        raise ScriptValidationError(f"traversed_path is empty: {traversed_path, final_value, paths}")

    # TODO: use one function twice instead reusing `graph.add_node` `get_destination`, `graph.add_edge` twice
    if traversed_path[0] in keywords_dict["GLOBAL"]: # TODO: will "GLOBAL" key be always into keywords_dict?
        graph.add_node("GLOBAL", ref=copy(paths[1])) # TODO: need more other flags like a fallback, global, etc.
        if traversed_path[1] in keywords_dict["TRANSITIONS"]:
            dst = get_destination(traversed_path[2])
            graph.add_edge(
                "GLOBAL",
                dst or "NONE", # TODO: Xmm, I think id of node can be nill/None , can we check it?
                label_ref=copy(paths[2]),
                label=traversed_path[2].display_value,
                cnd_ref=copy(paths[3]),
            )
    else:
        graph.add_node((traversed_path[0].absolute_value, traversed_path[1].absolute_value), ref=copy(paths[2]))
        if traversed_path[2] in keywords_dict["TRANSITIONS"]:
            dst = get_destination(traversed_path[3])
            graph.add_edge(
                (traversed_path[0].absolute_value, traversed_path[1].absolute_value),
                dst or "NONE",
                label_ref=copy(paths[3]),
                label=traversed_path[3].display_value,
                cnd_ref=copy(paths[4]) # TODO: use full name`condition_ref`
                # TODO: add `condition`
            )
