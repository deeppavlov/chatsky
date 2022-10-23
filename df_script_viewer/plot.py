import logging
import random
from typing import Dict

from df_script_parser.utils.validators import keywords_dict
import networkx as nx
import graphviz


VIRTUAL_FLOW_KEY = "virtual"
UNRESOLVED_KEY = "UNRESOLVED"
LOCAL = keywords_dict["LOCAL"][0].absolute_value
NODE_ATTRS = {
    "fontname": "Helvetica,Arial,sans-serif",
    "shape": "box",
    "style": "rounded, filled",
    "fillcolor": "#ffffff",
    "color": "#ffffff",
}


def get_random_colors():
    reserve = []
    for element in ["#96B0AF", "#C6AE82", "#F78378", "#FF7B9C", "#D289AB", "#86ACD5", "#86ACD5", "#F8D525", "#F6AE2D"]:
        yield element
        reserve.append("#{:06x}".format(random.randint(0, 0xFFFFFF)).upper())
    while reserve:
        for element in reserve:
            yield element


def format_name(name: tuple):
    name_value = str(name[1]).upper()
    if name_value == "NONE":
        name_value = UNRESOLVED_KEY
    return f"<tr><td><b>{name_value}</b></td></tr>"


def format_title(title: str):
    return f"<tr><td><b>{title}</b></td></tr>"


def format_lines(lines: list):
    return f"<tr><td>{'<br/>'.join(lines)}</td></tr>"


def format_port(name: str, port: str) -> str:
    return f'<tr><td port="{port}">{name}</td></tr>'


def format_as_table(rows: list) -> str:
    return "".join(['<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">', *rows, "</table>>"])


def transform_virtual(node: tuple):
    """
    Put nodes with no flow to a virtual flow, leave the rest unchanged.
    """
    if len(node) == 2:
        return node
    return (VIRTUAL_FLOW_KEY, node[0])


def get_plot(
    nx_graph: nx.Graph,
    show_misc: bool = False,
    show_response: bool = False,
    show_global: bool = False,
    show_local: bool = False,
    show_isolates: bool = True,
    **kwargs,
) -> graphviz.Digraph:
    graph = graphviz.Digraph()
    graph.attr(compound="true", splines="true", overlap="prism", fontname="Helvetica,Arial,sans-serif")
    graph.node_attr.update(**NODE_ATTRS)

    if not show_isolates:
        nx_graph.remove_nodes_from(list(nx.isolates(nx_graph)))

    nodes: Dict[str, Dict] = {}
    for edge, edge_data in nx_graph.edges.items():
        cur_node, next_node, _ = edge
        cur_node, next_node = transform_virtual(cur_node), transform_virtual(next_node)

        if not show_local and cur_node[1] == LOCAL:  # ignore local unless flag is set
            continue
        if not show_global and cur_node[1] == "GLOBAL":  # ignore local unless flag is set
            continue

        if cur_node not in nodes:
            nodes[cur_node] = {
                "name": str(cur_node),
                "label": [format_name(cur_node)],
                "transitions": {},
                "ports": [],
                "full_label": None,
            }

        port_id = str(hash(edge))  # port id is named after the edge
        nodes[cur_node]["ports"] += [format_port(edge_data["condition"], port_id)]
        nodes[cur_node]["transitions"][port_id] = str(next_node)  # port id mapped to the target node

    for node, node_data in nx_graph.nodes.items():  # add isolated nodes
        node = transform_virtual(node)
        if node not in nodes:

            if not show_local and node[1] == LOCAL:  # ignore local unless flag is set
                continue
            if not show_global and node[1] == "GLOBAL":  # ignore local unless flag is set
                continue

            nodes[node] = {
                "name": str(node),
                "label": [format_name(node)],
                "transitions": {},
                "ports": [],
                "full_label": None,
            }

        if show_response and "response" in node_data:
            nodes[node]["label"].append(format_title("Response"))
            nodes[node]["label"].extend(format_lines([node_data["response"].display_value]))

        if show_misc and "misc" in node_data:
            nodes[node]["label"].append(format_title("Misc"))
            nodes[node]["label"].extend(format_lines([str(node_data["misc"])]))

    flows: dict = {}

    for key in nodes.keys():
        flow, _ = key
        if flow not in flows:
            flows[flow] = graphviz.Digraph(name=f"cluster_{flow}")
            flows[flow].attr(label=str(flow).upper(), style="rounded, filled")
            if flow == VIRTUAL_FLOW_KEY:
                pass  # flows[flow].node_attr.update(bgcolor="transparent")

        if len(nodes[key]["ports"]) > 0:
            nodes[key]["label"].append(format_title("Transitions"))
            nodes[key]["label"].extend([*nodes[key]["ports"]])

        nodes[key]["full_label"] = format_as_table(nodes[key]["label"])
        flows[flow].node(name=nodes[key]["name"], label=nodes[key]["full_label"])

        for transition, dest in nodes[key]["transitions"].items():
            graph.edge(f"{key}:{transition}", dest)

    for color, subgraph in zip(get_random_colors(), flows.values()):
        subgraph.attr(color=color.lower())
        graph.subgraph(subgraph)

    graph = graph.unflatten(stagger=5, fanout=True)
    return graph
