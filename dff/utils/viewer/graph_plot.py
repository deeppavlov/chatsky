import random
from typing import Dict

import networkx as nx
import graphviz

from .utils import get_random_colors
from .preprocessing import get_script, UNRESOLVED_KEY


NODE_ATTRS = {
    "fontname": "Helvetica,Arial,sans-serif",
    "shape": "box",
    "style": "rounded, filled",
    "fillcolor": "#ffffffbf",
}


def format_name(name: str):
    """
    Format node name as graphviz html code.
    If the node name is 'NONE', replace it with the UNRESOLVED_KEY constant.
    """
    name_value = name.upper().strip("'")
    return f'<tr><td> <br align="left" /></td><td><b>{name_value}</b></td><td> <br align="right" /></td></tr>'


def format_title(title: str):  # second <br> to the left for spacing
    return f'<tr><td><br align="left" /> <br align="left" /></td><td><b>{title}</b></td><td> <br align="right" /></td></tr>'  # noqa: E501


def format_lines(lines: list):
    return f'<tr><td> <br align="left" /></td><td>{"<br/>".join(lines)}</td><td> <br align="right" /></td></tr>'


def format_port(name: str, port: str) -> str:
    return f'<tr><td>(<br align="left" /></td><td>{name}</td><td port="{port}">)<br align="right" /></td></tr>'


def format_as_table(rows: list) -> str:
    return "".join(['<<table border="0" cellborder="0" cellspacing="6" cellpadding="0">', *rows, "</table>>"])


def get_node_struct(node: tuple) -> Dict:
    """
    Get a formatted node structure.
    """
    return {
        "name": str(node),
        "label": [format_name(node[-1])],
        "transitions": {},
        "ports": [],
        "full_label": None,
    }


def get_script_data(script_node: dict, key: str, show_flag: bool) -> list:
    if not show_flag or key not in script_node:  # add response data
        return []
    return ["<hr/>", format_title(key.title()), format_lines([str(script_node[key])])]


def get_plot(
    nx_graph: nx.Graph,
    show_response: bool = False,
    show_processing: bool = False,
    show_misc: bool = False,
    random_seed: int = 1,
    **requirements,  # for cli integration
) -> graphviz.Digraph:
    random.seed(random_seed)

    graph = graphviz.Digraph()
    graph.attr(layout="osage", compound="true", splines="spline", overlap="ipsep", fontname="Helvetica,Arial,sans-serif")
    graph.node_attr.update(**NODE_ATTRS)

    nodes: Dict[str, Dict] = {}

    for node, node_data in nx_graph.nodes.items():
        if node not in nodes:
            node_struct = get_node_struct(node)
            nodes[node] = node_struct

        if node[-1] == UNRESOLVED_KEY:
            continue

        # get script data if necessary, add to node struct
        script_node = get_script(nx_graph, node_data)
        node_copy = list(node[1:])  # skip the initial NODE identifier
        while node_copy:  # recursively get node
            label_part = node_copy.pop(0)
            script_node = script_node.get(label_part, {})
        nodes[node]["label"].extend(get_script_data(script_node, "RESPONSE", show_response))
        nodes[node]["label"].extend(get_script_data(script_node, "PRE_RESPONSE_PROCESSING", show_processing))
        nodes[node]["label"].extend(get_script_data(script_node, "PRE_TRANSITIONS_PROCESSING", show_processing))
        nodes[node]["label"].extend(get_script_data(script_node, "MISC", show_misc))

    # add edge data to node structs
    for edge, edge_data in nx_graph.edges.items():
        edge_source_node, edge_target_node, _ = edge
        if edge_target_node not in nodes:
            continue  # ignore expelled nodes

        nodes[edge_source_node]["ports"] += [format_port(edge_data["condition"], edge_data["label"])]
        # port id mapped to the target node
        nodes[edge_source_node]["transitions"][edge_data["label"]] = str(edge_target_node)

    flows: dict = {}

    # add flows, nodes, edges to graphviz graph
    for key in nodes.keys():
        _, flow, _ = key
        if flow not in flows:
            flows[flow] = graphviz.Digraph(name=f"cluster_{flow}")
            flows[flow].attr(label=flow.upper().strip("'"), style="rounded, filled")

        if len(nodes[key]["ports"]) > 0:
            nodes[key]["label"].extend(["<hr/>", format_title("Transitions"), *nodes[key]["ports"]])

        nodes[key]["full_label"] = format_as_table(nodes[key]["label"])
        flows[flow].node(name=nodes[key]["name"], label=nodes[key]["full_label"])

        for transition, dest in nodes[key]["transitions"].items():
            graph.edge(f"{key}:{transition}", dest)

    for color, subgraph in zip(get_random_colors(), flows.values()):
        subgraph.attr(color=color.lower())
        graph.subgraph(subgraph)

    graph = graph.unflatten(stagger=5, fanout=True)
    return graph
