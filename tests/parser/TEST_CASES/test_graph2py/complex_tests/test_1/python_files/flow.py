from dff.core.engine.core.keywords import TRANSITIONS as TRANSITIONS
from dff.core.engine.core.keywords import RESPONSE as RESPONSE
from dff.core.engine.core.keywords import PROCESSING as PROCESSING
from dff.core.engine.core.keywords import LOCAL as LOCAL
import dff.core.engine.conditions as cnd
import dff.core.engine.labels as lbl
import re as re
from functions import add_prefix as add_prefix

global_flow = {
    LOCAL: {PROCESSING: {2: add_prefix("l2_local"), 3: add_prefix("l3_local")}},
    "start_node": {
        RESPONSE: "",
        TRANSITIONS: {
            ("music_flow", "node1"): cnd.regexp(r"talk about music"),
            ("greeting_flow", "node1"): cnd.regexp(r"hi|hello", re.IGNORECASE),
            "fallback_node": cnd.true(),
        },
    },
    "fallback_node": {
        RESPONSE: "Ooops",
        TRANSITIONS: {
            ("music_flow", "node1"): cnd.regexp(r"talk about music"),
            ("greeting_flow", "node1"): cnd.regexp(r"hi|hello", re.IGNORECASE),
            lbl.previous(): cnd.regexp(r"previous", re.IGNORECASE),
            lbl.repeat(): cnd.true(),
        },
    },
}
