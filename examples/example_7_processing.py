import logging


from df_engine.core.keywords import GLOBAL, LOCAL, RESPONSE, TRANSITIONS, PROCESSING
from df_engine.core import Context, Actor
import df_engine.labels as lbl
import df_engine.conditions as cnd

from examples import example_1_basics

logging.basicConfig(
    format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s", level=logging.DEBUG
)
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
    processed_node = ctx.a_s.get("processed_node", ctx.a_s["next_node"])
    processed_node.response = f"{ctx.last_label}: {processed_node.response}"
    ctx.a_s["processed_node"] = processed_node
    return ctx


def add_prefix(prefix):
    def add_prefix_processing(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
        processed_node = ctx.a_s.get("processed_node", ctx.a_s["next_node"])
        processed_node.response = f"{prefix}: {processed_node.response}"
        ctx.a_s["processed_node"] = processed_node
        return ctx

    return add_prefix_processing


# a dialog script
plot = {
    "root": {
        "start": {RESPONSE: "", TRANSITIONS: {("flow", "step_0"): cnd.true()}},
        "fallback": {RESPONSE: "the end"},
    },
    GLOBAL: {PROCESSING: {1: add_prefix("l1_global"), 2: add_prefix("l2_global")}},
    "flow": {
        LOCAL: {PROCESSING: {2: add_prefix("l2_local"), 3: add_prefix("l3_local")}},
        "step_0": {RESPONSE: "first", TRANSITIONS: {lbl.forward(): cnd.true()}},
        "step_1": {
            PROCESSING: {1: add_prefix("l1_step_1")},
            RESPONSE: "second",
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_2": {
            PROCESSING: {2: add_prefix("l2_step_2")},
            RESPONSE: "third",
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_3": {
            PROCESSING: {3: add_prefix("l3_step_3")},
            RESPONSE: "fourth",
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_4": {PROCESSING: {4: add_prefix("l4_step_4")}, RESPONSE: "fifth", TRANSITIONS: {"step_0": cnd.true()}},
    },
}


actor = Actor(plot, start_label=("root", "start"), fallback_label=("root", "fallback"))


# testing
testing_dialog = [
    ("", "l3_local: l2_local: l1_global: first"),
    ("", "l3_local: l2_local: l1_step_1: second"),
    ("", "l3_local: l2_step_2: l1_global: third"),
    ("", "l3_step_3: l2_local: l1_global: fourth"),
    ("", "l4_step_4: l3_local: l2_local: l1_global: fifth"),
    ("", "l3_local: l2_local: l1_global: first"),
]


def run_test():
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s", level=logging.INFO
    )
    # run_test()
    example_1_basics.run_interactive_mode(actor)
