"""
9. Pre-transitions processing
=============================
"""

# TODO:
# 1. Remove `create_transitions`
# 2. Rename start to start_node, fallback to fallback_node, step to node?

from dff.script import (
    GLOBAL,
    RESPONSE,
    TRANSITIONS,
    PRE_RESPONSE_PROCESSING,
    PRE_TRANSITIONS_PROCESSING,
    Context,
    Actor,
)
import dff.script.labels as lbl
import dff.script.conditions as cnd
from dff.pipeline import Pipeline
from dff.utils.testing import check_happy_path, is_interactive_mode, run_interactive_mode


def create_transitions():
    return {
        ("left", "step_2"): "left",
        ("right", "step_2"): "right",
        lbl.previous(): "previous",
        lbl.to_start(): "start",
        lbl.forward(): "forward",
        lbl.backward(): "back",
        lbl.previous(): "previous",
        lbl.repeat(): "repeat",
        lbl.to_fallback(): cnd.true(),
    }


def save_previous_node_response_to_ctx_processing(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
    processed_node = ctx.current_node
    ctx.misc["previous_node_response"] = processed_node.response
    return ctx


def get_previous_node_response_for_response_processing(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
    processed_node = ctx.current_node
    processed_node.response = f"previous={ctx.misc['previous_node_response']}: current={processed_node.response}"
    ctx.overwrite_current_node_in_processing(processed_node)
    return ctx


# a dialog script
toy_script = {
    "root": {
        "start": {RESPONSE: "", TRANSITIONS: {("flow", "step_0"): cnd.true()}},
        "fallback": {RESPONSE: "the end"},
    },
    GLOBAL: {
        PRE_RESPONSE_PROCESSING: {"proc_name_1": get_previous_node_response_for_response_processing},
        PRE_TRANSITIONS_PROCESSING: {"proc_name_1": save_previous_node_response_to_ctx_processing},
        TRANSITIONS: {lbl.forward(0.1): cnd.true()},
    },
    "flow": {
        "step_0": {RESPONSE: "first"},
        "step_1": {RESPONSE: "second"},
        "step_2": {RESPONSE: "third"},
        "step_3": {RESPONSE: "fourth"},
        "step_4": {RESPONSE: "fifth"},
    },
}


# testing
happy_path = (
    ("1", "previous=: current=first"),
    ("2", "previous=first: current=second"),
    ("3", "previous=second: current=third"),
    ("4", "previous=third: current=fourth"),
    ("5", "previous=fourth: current=fifth"),
)


pipeline = Pipeline.from_script(toy_script, start_label=("root", "start"), fallback_label=("root", "fallback"))

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
