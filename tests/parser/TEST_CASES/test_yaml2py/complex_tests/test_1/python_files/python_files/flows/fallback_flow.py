from python_files.nodes.fallback_node import fallback_node as fallback_node
from python_files.nodes import start_node as sn

fallback_flow = {"fallback_node": fallback_node, "other_node": sn.start_node}
