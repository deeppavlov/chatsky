import logging


from dff.core.engine.core.keywords import (
    GLOBAL,
    RESPONSE,
    TRANSITIONS,
    PRE_RESPONSE_PROCESSING,
    PRE_TRANSITIONS_PROCESSING,
)
from dff.core.engine.core import Context, Actor
import dff.core.engine.labels as lbl
import dff.core.engine.conditions as cnd

from . import example_1_basics

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
script = {
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


actor = Actor(script, start_label=("root", "start"), fallback_label=("root", "fallback"))


# testing
testing_dialog = [
    ("1", "previous=: current=first"),
    ("2", "previous=first: current=second"),
    ("3", "previous=second: current=third"),
    ("4", "previous=third: current=fourth"),
    ("5", "previous=fourth: current=fifth"),
]


def run_test():
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    # run_test()
    example_1_basics.run_interactive_mode(actor)
