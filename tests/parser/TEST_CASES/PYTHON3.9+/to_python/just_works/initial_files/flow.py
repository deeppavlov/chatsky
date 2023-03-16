from dff.script.core.keywords import TRANSITIONS, RESPONSE
import dff.script.conditions as cnd
import dff.script.labels.std_labels as lbl
import re


global_flow = {
    "start_node": {  # This is an initial node, it doesn't need an `RESPONSE`
        RESPONSE: "",
        TRANSITIONS: {
            ("music_flow", "node1"): cnd.regexp(r"talk about music"),  # first check
            ("greeting_flow", "node1"): cnd.regexp(
                r"hi|hello", re.IGNORECASE
            ),  # second check
            # ("global_flow", "fallback_node"): cnd.true(),  # third check
            "fallback_node": cnd.true(),  # third check
            # "fallback_node" is equivalent to ("global_flow", "fallback_node")
        },
    },
    "fallback_node": {  # We get to this node if an error occurred while the agent was running
        RESPONSE: "Ooops",
        TRANSITIONS: {
            ("music_flow", "node1"): cnd.regexp(r"talk about music"),  # first check
            ("greeting_flow", "node1"): cnd.regexp(
                r"hi|hello", re.IGNORECASE
            ),  # second check
            lbl.previous(): cnd.regexp(r"previous", re.IGNORECASE),  # third check
            # lbl.previous() is equivalent to ("PREVIOUS_flow", "PREVIOUS_node")
            lbl.repeat(): cnd.true(),  # fourth check
            # lbl.repeat() is equivalent to ("global_flow", "fallback_node")
        },
    },
}
