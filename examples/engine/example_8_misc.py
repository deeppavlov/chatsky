"""
8. Misc
=======
"""

import logging
from typing import Any


from dff.core.engine.core.keywords import GLOBAL, LOCAL, RESPONSE, TRANSITIONS, MISC
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


def custom_response(ctx: Context, actor: Actor, *args, **kwargs) -> Any:
    if ctx.validation:
        return ""
    current_node = ctx.current_node
    return f"ctx.last_label={ctx.last_label}: current_node.misc={current_node.misc}"


# a dialog script
script = {
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


actor = Actor(script, start_label=("root", "start"), fallback_label=("root", "fallback"))


# testing
testing_dialog = [
    (
        "",
        "ctx.last_label=('flow', 'step_0'): "
        "current_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_0'}",
    ),
    (
        "",
        "ctx.last_label=('flow', 'step_1'): "
        "current_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_1'}",
    ),
    (
        "",
        "ctx.last_label=('flow', 'step_2'): "
        "current_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_2'}",
    ),
    (
        "",
        "ctx.last_label=('flow', 'step_3'): "
        "current_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_3'}",
    ),
    (
        "",
        "ctx.last_label=('flow', 'step_4'): "
        "current_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_4'}",
    ),
    (
        "",
        "ctx.last_label=('flow', 'step_0'): "
        "current_node.misc={'var1': 'global_data', 'var2': 'rewrite_by_local', 'var3': 'info_of_step_0'}",
    ),
]


if __name__ == "__main__":
    if get_auto_arg():
        run_auto_mode(actor, testing_dialog, logger)
    else:
        run_interactive_mode(actor, logger)
