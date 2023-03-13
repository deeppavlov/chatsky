from dff.script.core.keywords import (
    TRANSITIONS,
)
from dff.pipeline import Pipeline
import dff.script.conditions as cnd
import dff.script.labels as lbl

priority = 56


script = {
    "flow": {
        "node": {
            TRANSITIONS: {
                lbl.to_fallback(priority, other="str", another=("tuple",)): cnd.true(),
            }
        }
    }
}

pipeline = Pipeline.from_script(script, ("flow", "node"))
