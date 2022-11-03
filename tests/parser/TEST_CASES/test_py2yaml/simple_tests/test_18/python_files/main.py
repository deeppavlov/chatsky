from dff.core.engine.core import Actor as act
import dff.core.engine.core.keywords as kw
import dff.core.engine.conditions as cnd

actor = act(
    {
        "flow1": {
            "node": {
                kw.RESPONSE: "hey",
                kw.TRANSITIONS: {
                    ("flow2", "node"): cnd.true()
                }
            }
        },
        "flow2": {
            "node": {
                kw.RESPONSE: "hi",
                kw.TRANSITIONS: {
                    ("flow1", "node"): cnd.true()
                }
            }
        }
    },
    ("flow1", "node")
)