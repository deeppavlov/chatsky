import logging
from typing import Any


from df_engine.core.keywords import GLOBAL, LOCAL, RESPONSE, TRANSITIONS, MISC
from df_engine.core import Context, Actor
import df_engine.labels as lbl
import df_engine.conditions as cnd

from examples import example_1_basics

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


def custom_response(ctx: Context, actor: Actor, *args, **kwargs) -> Any:
    if ctx.validation:
        return ""
    processed_node = ctx.framework_states["actor"]["processed_node"]
    return f"ctx.last_label={ctx.last_label}: processed_node.misc={processed_node.misc}"


# a dialog script
plot = {
    "root": {
        "start": {RESPONSE: "", TRANSITIONS: {("flow", "step_0"): cnd.true()}},
        "fallback": {RESPONSE: "the end"},
    },
    GLOBAL: {
        MISC: {
            "var1": "global_data",
            "var2": "global_data",
            "var3": "global_data",
        }
    },
    "flow": {
        LOCAL: {
            MISC: {
                "var2": "rewrite_by_local",
                "var3": "rewrite_by_local",
            }
        },
        "step_0": {
            MISC: {"var3": "info_of_step_0"},
            RESPONSE: custom_response,
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_1": {
            MISC: {"var3": "info_of_step_1"},
            RESPONSE: custom_response,
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_2": {
            MISC: {"var3": "info_of_step_2"},
            RESPONSE: custom_response,
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_3": {
            MISC: {"var3": "info_of_step_3"},
            RESPONSE: custom_response,
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_4": {MISC: {"var3": "info_of_step_4"}, RESPONSE: custom_response, TRANSITIONS: {"step_0": cnd.true()}},
    },
}


actor = Actor(plot, start_label=("root", "start"), fallback_label=("root", "fallback"))


# testing
testing_dialog = [
    (
        "",
        "ctx.last_label=('flow', 'step_0'): processed_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_0'}",
    ),
    (
        "",
        "ctx.last_label=('flow', 'step_1'): processed_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_1'}",
    ),
    (
        "",
        "ctx.last_label=('flow', 'step_2'): processed_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_2'}",
    ),
    (
        "",
        "ctx.last_label=('flow', 'step_3'): processed_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_3'}",
    ),
    (
        "",
        "ctx.last_label=('flow', 'step_4'): processed_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_4'}",
    ),
    (
        "",
        "ctx.last_label=('flow', 'step_0'): processed_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_0'}",
    ),
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
    run_test()
    example_1_basics.run_interactive_mode(actor)
