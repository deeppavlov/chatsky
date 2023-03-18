import random
from typing import Dict

import networkx as nx
import graphviz


VIRTUAL_FLOW_KEY = "virtual"
UNRESOLVED_KEY = "UNRESOLVED"
NODE_ATTRS = {
    "fontname": "Helvetica,Arial,sans-serif",
    "shape": "box",
    "style": "rounded, filled",
    "fillcolor": "#ffffffbf",
}


def get_random_colors():
    target_colors = ["#96B0AF", "#C6AE82", "#F78378", "#FF7B9C", "#D289AB", "#86ACD5", "#86ACD5", "#F8D525", "#F6AE2D"]
    reserve = []
    for element in target_colors:
        yield element
        reserve.append(random.choice(target_colors))
    while reserve:
        for element in reserve:
            yield element


def format_name(name: str):
    """
    Format node name as graphviz html code.
    If the node name is 'NONE', replace it with the UNRESOLVED_KEY constant.
    """
    name_value = name.upper().strip("'")
    if name_value == "NONE":
        name_value = UNRESOLVED_KEY
    return f'<tr><td> <br align="left" /></td><td><b>{name_value}</b></td><td> <br align="right" /></td></tr>'


def format_title(title: str):  # second <br> to the left for spacing
    return f'<tr><td><br align="left" /> <br align="left" /></td><td><b>{title}</b></td><td> <br align="right" /></td></tr>'


def format_lines(lines: list):
    return f'<tr><td> <br align="left" /></td><td>{"<br/>".join(lines)}</td><td> <br align="right" /></td></tr>'


def format_port(name: str, port: str) -> str:
    return f'<tr><td>(<br align="left" /></td><td>{name}</td><td port="{port}">)<br align="right" /></td></tr>'


def format_as_table(rows: list) -> str:
    return "".join(['<<table border="0" cellborder="0" cellspacing="6" cellpadding="0">', *rows, "</table>>"])


def transform_virtual(node: tuple):
    """
    Normal nodes have label length == 3.
    This function adds nodes without a flow (label length == 2) to a virtual flow.
    Leaves nodes of other type unchanged.
    """
    if len(node) == 3:
        return node
    elif len(node) <= 2:
        return (node[0], VIRTUAL_FLOW_KEY, node[-1])
    else:
        print(node)
        raise RuntimeError(f"Too many parts in node name: {len(node)}")


def get_plot(
    nx_graph: nx.Graph,
    show_misc: bool = False,
    show_response: bool = False,
    show_global: bool = False,
    show_local: bool = False,
    show_isolates: bool = True,
    random_seed: int = 1,
) -> graphviz.Digraph:
    random.seed(random_seed)

    graph = graphviz.Digraph()
    graph.attr(compound="true", splines="true", overlap="prism", fontname="Helvetica,Arial,sans-serif")
    graph.node_attr.update(**NODE_ATTRS)

    if not show_isolates:
        nx_graph.remove_nodes_from(list(nx.isolates(nx_graph)))

    nodes: Dict[str, Dict] = {}
    for edge, edge_data in nx_graph.edges.items():
        edge_source_node, edge_target_node, _ = edge
        if edge_source_node[0] == "LABEL" or edge_target_node[0] == "LABEL":
            continue
        edge_source_node = transform_virtual(edge_source_node)
        edge_target_node = transform_virtual(edge_target_node)
        _, _, source_name = edge_source_node

        if not show_local and source_name == "LOCAL":  # ignore local unless flag is set
            continue

        if not show_global and source_name == "GLOBAL":  # ignore global unless flag is set
            continue

        if edge_source_node not in nodes:
            nodes[edge_source_node] = {
                "name": str(edge_source_node),
                "label": [format_name(source_name)],
                "transitions": {},
                "ports": [],
                "full_label": None,
            }

        port_id = edge_data["label"]  # port id is named after the edge
        nodes[edge_source_node]["ports"] += [format_port(edge_data["condition"], port_id)]
        nodes[edge_source_node]["transitions"][port_id] = str(edge_target_node)  # port id mapped to the target node

    for node, node_data in nx_graph.nodes.items():  # add isolated nodes
        if not show_isolates:
            break

        if node[0] == "LABEL":
            continue
        if node not in nodes:
            node = transform_virtual(node)
            _, _, node_name = node

            if not show_local and node_name == "LOCAL":  # ignore local unless flag is set
                continue

            if not show_global and node_name == "GLOBAL":  # ignore global unless flag is set
                continue

            nodes[node] = {
                "name": str(node),
                "label": [format_name(node_name)],
                "transitions": {},
                "ports": [],
                "full_label": None,
            }

        if node[0] == "NONE":
            continue

        namespace, script_name, *_ = node_data["ref"]  # get namespace from ref
        script_node = nx_graph.graph["full_script"].get(namespace, {}).get(script_name, {})

        node_copy = list(node[1:])  # skip the initial NODE identifier
        while node_copy:
            label_part = node_copy.pop(0)
            script_node = script_node.get(label_part, {})

        if show_response and "RESPONSE" in script_node:  # add response data
            nodes[node]["label"].append("<hr/>")
            nodes[node]["label"].append(format_title("Response"))
            nodes[node]["label"].extend(format_lines([script_node["RESPONSE"]]))

        if show_misc and "MISC" in script_node:  # add misc data
            nodes[node]["label"].append("<hr/>")
            nodes[node]["label"].append(format_title("Misc"))
            nodes[node]["label"].extend(format_lines([str(script_node["MISC"])]))

    flows: dict = {}

    for key in nodes.keys():
        _, flow, _ = key
        if flow not in flows:
            flows[flow] = graphviz.Digraph(name=f"cluster_{flow}")
            flows[flow].attr(label=flow.upper().strip("'"), style="rounded, filled")

        if len(nodes[key]["ports"]) > 0:
            nodes[key]["label"].append("<hr/>")
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
