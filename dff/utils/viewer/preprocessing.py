import networkx as nx
import pandas as pd

VIRTUAL_FLOW_KEY = "virtual"
UNRESOLVED_KEY = "UNRESOLVED"


def get_script(nx_graph: nx.Graph, node_data: dict) -> dict:
    namespace, script_name, *_ = node_data["ref"]  # get namespace from ref
    script = nx_graph.graph["full_script"].get(namespace, {}).get(script_name, {})
    return script


def get_label_by_index_shifting(
    nx_graph: nx.Graph, node_id: tuple, increment_flag: bool = True, cyclicality_flag: bool = True
) -> tuple:
    if node_id == ("NONE",) or node_id == ("GLOBAL_NODE", "GLOBAL"):  # fall back on skip conditions
        return ("NODE", *nx_graph.graph["fallback_label"])
    script = get_script(nx_graph, nx_graph.nodes[node_id])
    _, flow, *info = node_id
    labels = list(script[flow])
    node_label = info[0]
    if node_label not in labels:
        return ("NODE", *nx_graph.graph["fallback_label"])

    label_index = labels.index(node_label)
    label_index = label_index + 1 if increment_flag else label_index - 1
    if not (cyclicality_flag or (0 <= label_index < len(labels))):
        return ("NODE", *nx_graph.graph["fallback_label"])
    label_index %= len(labels)
    if labels[label_index] == "LOCAL":  # cannot transition into 'LOCAL'
        return ("NODE", *nx_graph.graph["fallback_label"])
    return ("NODE", flow, labels[label_index])


def resolve_labels(nx_graph: nx.Graph, edge: tuple, edge_data: dict) -> dict:
    source_node, target_node, *edge_info = edge
    _, label_type, *_ = target_node
    _, *source_info = source_node

    # get label transition sources
    if source_info[0] == "GLOBAL_NODE":
        sources = [node for node in nx_graph.nodes.keys() if node[0] != "LABEL" and node[0] != "NONE"]
    elif source_info[0] == "LOCAL_NODE":
        sources = [node for node in nx_graph.nodes.keys() if node[1] == source_info[0] and node[0] != "NONE"]
    else:
        sources = [source_node]

    # get label transiton targets
    if label_type == "repeat":
        targets = sources
    elif label_type == "to_fallback":
        targets = [("NODE", *nx_graph.graph["fallback_label"])] * len(sources)
    elif label_type == "to_start":
        targets = [("NODE", *nx_graph.graph["start_label"])] * len(sources)
    elif label_type == "forward":
        targets = [get_label_by_index_shifting(nx_graph, node_id, increment_flag=True) for node_id in sources]
    elif label_type == "backward":
        targets = [get_label_by_index_shifting(nx_graph, node_id, increment_flag=False) for node_id in sources]
    else:
        return {}
    new_data = edge_data.copy()
    new_data["label"] = label_type
    return [(s, t, new_data) for s, t in zip(sources, targets)]


def transform_virtual(node: tuple):
    """
    Put special nodes to virtual flow. Replace NONE with unresolved key constant.
    """
    if node == ("GLOBAL_NODE", "GLOBAL"):
        return ("NODE", VIRTUAL_FLOW_KEY, node[-1])
    elif node == ("NONE",):
        return ("NODE", VIRTUAL_FLOW_KEY, UNRESOLVED_KEY)
    return node


def preprocess(
    nx_graph: nx.Graph,
    show_global: bool = False,
    show_local: bool = False,
    show_unresolved: bool = False,
    show_isolates: bool = True,
    **kwargs,  # for cli integration
) -> nx.Graph:

    label_edges = []
    for edge, edge_data in nx_graph.edges.items():
        if edge[1][0] != "LABEL":
            continue
        label_edges += resolve_labels(nx_graph, edge, edge_data)
    nx_graph.add_edges_from(label_edges)

    nx_graph.remove_nodes_from(list(node for node in nx_graph.nodes if node[0] == "LABEL"))

    if not show_global and ("GLOBAL_NODE", "GLOBAL") in nx_graph.nodes:
        nx_graph.remove_nodes_from([("GLOBAL_NODE", "GLOBAL")])

    if not show_local:
        nx_graph.remove_nodes_from(list(node for node in nx_graph.nodes if node[-1] == "LOCAL"))

    if not show_unresolved and ("NONE",) in nx_graph.nodes:
        nx_graph.remove_nodes_from([("NONE",)])

    if not show_isolates:
        nx_graph.remove_nodes_from(list(nx.isolates(nx_graph)))

    nx_graph = nx.relabel_nodes(nx_graph, {name: transform_virtual(name) for name in nx_graph.nodes.keys()})

    return nx_graph


def get_adjacency_dataframe(nx_graph: nx.Graph) -> pd.DataFrame:
    matrix = nx.adjacency_matrix(nx_graph).toarray()
    df = pd.DataFrame(
        matrix, index=[str(x[:3]) for x in nx_graph.nodes.keys()], columns=[str(x[:3]) for x in nx_graph.nodes.keys()]
    )
    df = df.loc[(df != 0).any(axis=1), (df != 0).any(axis=0)]
    df = df.reindex(sorted(df.columns), axis=1).reindex(sorted(df.index), axis=0)
    return df
