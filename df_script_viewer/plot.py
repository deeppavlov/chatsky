import random
from typing import Dict

import networkx as nx
import graphviz


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


def format_name(name: str):
    return f"<tr><td><b>{name}</b></td></tr>"


def format_lines(lines: list):
    return f"<tr><td>{'<br/>'.join(lines)}</td></tr>"


def format_port(name: str, port: str) -> str:
    return f'<tr><td port="{port}">{name}</td></tr>'


def format_as_table(rows: list) -> str:
    return "".join(['<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">', *rows, "</table>>"])


def get_plot(nx_graph: nx.Graph) -> bytes:
    graph = graphviz.Digraph()
    graph.attr(compound="true", splines="true", overlap="prism")
    graph.node_attr.update(**NODE_ATTRS)

    nodes: Dict[str, Dict] = {}
    for edge, edge_data in nx_graph.edges.items():
        if edge[0] not in nodes:
            nodes[edge[0]] = {"name": str(edge[0]), "label": [], "transitions": {}}
        if edge[1] not in nodes:
            nodes[edge[1]] = {"name": str(edge[1]), "label": [], "transitions": {}}
        nodes[edge[0]]["label"] += [
            format_port(edge_data["condition"], str(hash(edge)))
        ]  # port id is named after the edge

        nodes[edge[0]]["transitions"][hash(edge)] = str(edge[1])  # port id mapped to the target node

    flows: dict = {}

    for key in nodes.keys():
        if key[0] not in flows:
            flows[key[0]] = graphviz.Digraph(name=f"cluster_{key[0]}")
            flows[key[0]].attr(label=str(key[0]), style="rounded, filled")

        nodes[key]["label"] = format_as_table(
            [
                format_name(key),
                *nodes[key]["label"],
            ]
        )
        flows[key[0]].node(name=nodes[key]["name"], label="".join(nodes[key]["label"]))
        for transition, dest in nodes[key]["transitions"].items():
            graph.edge(f"{key}:{transition}", dest)

    for color, subgraph in zip(get_random_colors(), flows.values()):
        subgraph.attr(color=color.lower())
        graph.subgraph(subgraph)

    graph = graph.unflatten(stagger=5, fanout=True)
    _bytes = graph.pipe(format="png")
    return _bytes
