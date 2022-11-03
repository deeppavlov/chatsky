import module
from dff.core.engine.core.keywords import TRANSITIONS, GLOBAL
from dff.core.engine.core.actor import Actor

glob = {"glob": GLOBAL}

flow = {"flow": "flow"}

act = Actor(
    {
        glob["glob"]: {
            TRANSITIONS: {module.consts.there[module.node1.ints[module.node1.ints[3]]]: module.proxy.node1.ints[3]}
        },
        flow["flow"]: {
            "node1": module.proxy.node1.node,
            module.proxy.node1.d[2][3]: module.node1.node,
        },
        "flow2": {"node1": module.proxy.node1.node},
    },
    start_label=("flow", "node1"),
)
