# %% [markdown]
"""
# Core: 7. Pre-response processing

This tutorial shows pre-response processing feature.

Here, [PRE_RESPONSE_PROCESSING](https://deeppavlov.github.io/dialog_flow_framework/apiref/dff.script.core.keywords.html#dff.script.core.keywords.Keywords.PRE_RESPONSE_PROCESSING)
that can be used for additional context processing before response is shown.

First of all, let's do all the necessary imports from DFF.
"""  # noqa: E501


# %%
from dff.script import (
    GLOBAL,
    LOCAL,
    RESPONSE,
    TRANSITIONS,
    PRE_RESPONSE_PROCESSING,
    Context,
    Message,
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
def add_label_processing(ctx: Context, _: Pipeline, *args, **kwargs) -> Context:
    processed_node = ctx.current_node
    processed_node.response = Message(text=f"{ctx.last_label}: {processed_node.response.text}")
    ctx.overwrite_current_node_in_processing(processed_node)
    return ctx


def add_prefix(prefix):
    def add_prefix_processing(ctx: Context, _: Pipeline, *args, **kwargs) -> Context:
        processed_node = ctx.current_node
        processed_node.response = Message(text=f"{prefix}: {processed_node.response.text}")
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
        "start": {RESPONSE: Message(), TRANSITIONS: {("flow", "step_0"): cnd.true()}},
        "fallback": {RESPONSE: Message(text="the end")},
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
        "step_0": {RESPONSE: Message(text="first"), TRANSITIONS: {lbl.forward(): cnd.true()}},
        "step_1": {
            PRE_RESPONSE_PROCESSING: {"proc_name_1": add_prefix("l1_step_1")},
            RESPONSE: Message(text="second"),
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_2": {
            PRE_RESPONSE_PROCESSING: {"proc_name_2": add_prefix("l2_step_2")},
            RESPONSE: Message(text="third"),
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_3": {
            PRE_RESPONSE_PROCESSING: {"proc_name_3": add_prefix("l3_step_3")},
            RESPONSE: Message(text="fourth"),
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_4": {
            PRE_RESPONSE_PROCESSING: {"proc_name_4": add_prefix("l4_step_4")},
            RESPONSE: Message(text="fifth"),
            TRANSITIONS: {"step_0": cnd.true()},
        },
    },
}


# testing
happy_path = (
    (Message(), Message(text="l3_local: l2_local: l1_global: first")),
    (Message(), Message(text="l3_local: l2_local: l1_step_1: second")),
    (Message(), Message(text="l3_local: l2_step_2: l1_global: third")),
    (Message(), Message(text="l3_step_3: l2_local: l1_global: fourth")),
    (Message(), Message(text="l4_step_4: l3_local: l2_local: l1_global: fifth")),
    (Message(), Message(text="l3_local: l2_local: l1_global: first")),
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
