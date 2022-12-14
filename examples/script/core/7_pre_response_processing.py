# %% [markdown]
"""
# 7. Pre-response processing

This example shows pre-response processing feature.
First of all, let's do all the necessary imports from `dff`.
"""


# %%
from dff.script import (
    GLOBAL,
    LOCAL,
    RESPONSE,
    TRANSITIONS,
    PRE_RESPONSE_PROCESSING,
    Context,
    Actor,
)
import dff.script.labels as lbl
import dff.script.conditions as cnd

from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)


# %%
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


# %% [markdown]
"""
`PRE_RESPONSE_PROCESSING` is a keyword that
can be used in `GLOBAL`, `LOCAL` or nodes.
"""


# %%
toy_script = {
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
            PRE_RESPONSE_PROCESSING: {
                "proc_name_2": add_prefix("l2_local"),
                "proc_name_3": add_prefix("l3_local"),
            }
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


# testing
happy_path = (
    ("", "l3_local: l2_local: l1_global: first"),
    ("", "l3_local: l2_local: l1_step_1: second"),
    ("", "l3_local: l2_step_2: l1_global: third"),
    ("", "l3_step_3: l2_local: l1_global: fourth"),
    ("", "l4_step_4: l3_local: l2_local: l1_global: fifth"),
    ("", "l3_local: l2_local: l1_global: first"),
)


# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
