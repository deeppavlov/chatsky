from ..nodes import sn
from ..nodes.fallback_node import fallback_node

start_flow = {
    "start_node": sn,
    "other_node": fallback_node,
}
