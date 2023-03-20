import random
from typing import Dict, Optional

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
    return f'<tr><td><br align="left" /> <br align="left" /></td><td><b>{title}</b></td><td> <br align="right" /></td></tr>'  # noqa: E501


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


def get_node_struct(node: tuple, show_local: bool, show_global: bool) -> Optional[Dict]:
    """
    Get a formatted node structure.
    """
    _, _, node_name = node

    if not show_local and node_name == "LOCAL":  # ignore local unless flag is set
        return None

    if not show_global and node_name == "GLOBAL":  # ignore global unless flag is set
        return None

    return {
        "name": str(node),
        "label": [format_name(node_name)],
        "transitions": {},
        "ports": [],
        "full_label": None,
    }


def get_script_data(script_node: dict, key: str, show_flag: bool) -> list:
    if not show_flag or not key in script_node:  # add response data
        return []
    return ["<hr/>", format_title(key.title()), format_lines([str(script_node[key])])]


def resolve_labels(nx_graph: nx.Graph, edge: tuple, edge_data: dict) -> dict:
    source_node, target_node, *edge_info = edge
    _, label_type, *_ = target_node
    _, *source_info = source_node

    # get label transition sources
    if source_info[0] == "GLOBAL":
        sources = [node for node in nx_graph.nodes.keys() if node[0] != "LABEL"]
    elif source_info[1] == "LOCAL":
        sources = [node for node in nx_graph.nodes.keys() if node[1] == source_info[0]]
    else:
        sources = [source_node]

    # get label transiton targets
    if label_type == "repeat":
        targets = sources
    elif label_type == "to_fallback":
        targets = [("NODE", *nx_graph.graph["fallback_label"])] * len(sources)
    elif label_type == "to_start":
        targets = [("NODE", *nx_graph.graph["start_label"])] * len(sources)
    else:  # TODO: add forward && backward
        return {}
    new_data = edge_data.copy()
    new_data["label"] = label_type
    return {(s, t, *edge_info): new_data for s, t in zip(sources, targets)}


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

    for node, node_data in nx_graph.nodes.items():  # add isolated nodes
        if node[0] == "LABEL":
            continue

        # add node struct
        if node not in nodes:
            node = transform_virtual(node)
            node_struct = get_node_struct(node, show_local, show_global)
            if node_struct is None:
                continue  # ignore locals and globals when flag is not set
            nodes[node] = node_struct

        if node[0] == "NONE":
            continue

        # get script data if necessary, add to node struct
        namespace, script_name, *_ = node_data["ref"]  # get namespace from ref
        script_node = nx_graph.graph["full_script"].get(namespace, {}).get(script_name, {})
        node_copy = list(node[1:])  # skip the initial NODE identifier
        while node_copy:
            label_part = node_copy.pop(0)
            script_node = script_node.get(label_part, {})
        nodes[node]["label"].extend(get_script_data(script_node, "RESPONSE", show_response))
        nodes[node]["label"].extend(get_script_data(script_node, "MISC", show_misc))

    label_edges = dict(nx_graph.edges)

    # first iteration: add label edges;
    # remove edges that end in labels
    for edge, edge_data in nx_graph.edges.items():
        if edge[1][0] != "LABEL":
            continue
        label_edges.update(resolve_labels(nx_graph, edge, edge_data))
        label_edges.pop(edge)

    # second iteration: add edge data to node structs
    for edge, edge_data in label_edges.items():
        edge_source_node, edge_target_node, _ = edge
        edge_source_node = transform_virtual(edge_source_node)
        edge_target_node = transform_virtual(edge_target_node)
        if get_node_struct(edge_source_node, show_local, show_global) is None:
            continue  # ignore locals and globals when flags are not set

        nodes[edge_source_node]["ports"] += [format_port(edge_data["condition"], edge_data["label"])]
        nodes[edge_source_node]["transitions"][edge_data["label"]] = str(
            edge_target_node
        )  # port id mapped to the target node

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
