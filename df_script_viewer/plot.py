import random
from io import BytesIO
from base64 import b64encode
from collections import Iterable

import networkx as nx
import graphviz
import plotly.graph_objects as go
from plotly.colors import qualitative


NODE_ATTRS = {
    "fontname": "Helvetica,Arial,sans-serif",
    "shape": "plain",
    "style": "filled",
}


def get_random_colors():
    reserve = []
    for element in qualitative.Plotly:
        yield element
        reserve.append("#{:06x}".format(random.randint(0, 0xFFFFFF)).upper())
    while reserve:
        for element in reserve:
            yield element


def get_html_label(name: str, **kwargs) -> str:
    rows = [f"<tr><td><b>{name}</b></td></tr>"]
    for key, value in kwargs.items():
        rows.append(f"<tr><td><b>{key}</b></td></tr>")
        if isinstance(value, str):
            line = f"<tr><td>{value}</td></tr>"
        elif isinstance(value, Iterable):
            line_sep = "<br/>".join(value)
            line = f"<tr><td>{line_sep}</td></tr>"
        rows.append(line)

    return "".join(['<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">', *rows, "</table>>"])


def get_plot(nx_graph: nx.Graph) -> bytes:
    graph = graphviz.Digraph(engine="fdp")
    graph.attr(compound="true", splines="true", overlap="prism")
    graph.node_attr.update(**NODE_ATTRS)
    flows = dict()
    for node, node_data in nx_graph.nodes.items():
        if not flows.get(node[0]):
            flows[node[0]] = dict()
        flows[node[0]][node] = node_data

    for color, flow in zip(get_random_colors(), flows.keys()):
        color = color.lower()
        with graph.subgraph(name=flow) as flow_graph:
            flow_graph.attr(label=flow)
            for node, node_data in flows[flow].items():
                name = str(node)
                label = get_html_label(name, **node_data)
                flow_graph.node(name, label=label, style="filled", fillcolor=color, fontcolor="white")

    for edge, edge_data in nx_graph.edges.items():
        name = str(edge)
        label = get_html_label(name, **edge_data)
        graph.node(name, label=label, style="filled", fillcolor="gray95")
        graph.edge(name, str(edge[1]))
        graph.edge(str(edge[0]), name)

    graph = graph.unflatten(stagger=5, fanout=True)
    _bytes = graph.pipe(format="png")
    return _bytes
