import logging


from dff.core.keywords import RESPONSE, TRANSITIONS, PROCESSING
from dff.core import Context, Actor
import dff.labels as lbl
import dff.conditions as cnd

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
        "start": {
            RESPONSE: "",
            TRANSITIONS: {("greeting", "step_0"): cnd.true()},
        },
        "fallback": {RESPONSE: "the end"},
    },
    "greeting": {
        "step_0": {
            PROCESSING: {1: add_label_processing, 2: add_prefix("prefix_1")},
            RESPONSE: "hi",
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_1": {
            PROCESSING: {1: add_label_processing, 2: add_prefix("prefix_2")},
            RESPONSE: "what's up",
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_2": {
            PROCESSING: {1: add_label_processing, 2: add_prefix("prefix_3")},
            RESPONSE: "ok",
        },
    },
}


actor = Actor(plot, start_label=("root", "start"), fallback_label=("root", "fallback"))


# testing
testing_dialog = [
    ("Hi", "prefix_1: ('greeting', 'step_0'): hi"),
    ("Ok", "prefix_2: ('greeting', 'step_1'): what's up"),
    ("i'm fine", "prefix_3: ('greeting', 'step_2'): ok"),
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
