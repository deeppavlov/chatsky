"""
7. Pre-response processing
==========================
"""

# TODO:
# 1. Remove `create_transitions` - doesn't use

import logging

from dff.core.engine.core.keywords import GLOBAL, LOCAL, RESPONSE, TRANSITIONS, PRE_RESPONSE_PROCESSING
from dff.core.engine.core import Context, Actor
import dff.core.engine.labels as lbl
import dff.core.engine.conditions as cnd
from examples.engine._engine_utils import run_auto_mode, run_interactive_mode
from examples.utils import get_auto_arg

logger = logging.getLogger(__name__)


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


def add_label_processing(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
    processed_node = ctx.current_node
    processed_node.response = f"{ctx.last_label}: {processed_node.response}"
    ctx.overwrite_current_node_in_processing(processed_node)
    return ctx


def add_prefix(prefix):
    def add_prefix_processing(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
        processed_node = ctx.current_node
        processed_node.response = f"{prefix}: {processed_node.response}"
        ctx.overwrite_current_node_in_processing(processed_node)
        return ctx

    return add_prefix_processing


# a dialog script
script = {
    "root": {
        "start": {RESPONSE: "", TRANSITIONS: {("flow", "step_0"): cnd.true()}},
        "fallback": {RESPONSE: "the end"},
    },
    GLOBAL: {
        PRE_RESPONSE_PROCESSING: {
            "proc_name_1": add_prefix("l1_global"),
            "proc_name_2": add_prefix("l2_global"),
        }
    },
    "flow": {
        LOCAL: {
            PRE_RESPONSE_PROCESSING: {"proc_name_2": add_prefix("l2_local"), "proc_name_3": add_prefix("l3_local")}
        },
        "step_0": {RESPONSE: "first", TRANSITIONS: {lbl.forward(): cnd.true()}},
        "step_1": {
            PRE_RESPONSE_PROCESSING: {"proc_name_1": add_prefix("l1_step_1")},
            RESPONSE: "second",
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_2": {
            PRE_RESPONSE_PROCESSING: {"proc_name_2": add_prefix("l2_step_2")},
            RESPONSE: "third",
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_3": {
            PRE_RESPONSE_PROCESSING: {"proc_name_3": add_prefix("l3_step_3")},
            RESPONSE: "fourth",
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_4": {
            PRE_RESPONSE_PROCESSING: {"proc_name_4": add_prefix("l4_step_4")},
            RESPONSE: "fifth",
            TRANSITIONS: {"step_0": cnd.true()},
        },
    },
}


actor = Actor(script, start_label=("root", "start"), fallback_label=("root", "fallback"))


# testing
testing_dialog = [
    ("", "l3_local: l2_local: l1_global: first"),
    ("", "l3_local: l2_local: l1_step_1: second"),
    ("", "l3_local: l2_step_2: l1_global: third"),
    ("", "l3_step_3: l2_local: l1_global: fourth"),
    ("", "l4_step_4: l3_local: l2_local: l1_global: fifth"),
    ("", "l3_local: l2_local: l1_global: first"),
]


if __name__ == "__main__":
    if get_auto_arg():
        run_auto_mode(actor, testing_dialog, logger)
    else:
        run_interactive_mode(actor, logger)
