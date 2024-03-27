# %% [markdown]
"""
# Core: 7. Pre-response processing

This tutorial shows pre-response processing feature.

Here, %mddoclink(api,script.core.keywords,Keywords.PRE_RESPONSE_PROCESSING)
is demonstrated which can be used for
additional context processing before response handlers.

There are also some other %mddoclink(api,script.core.keywords,Keywords)
worth attention used in this tutorial.

First of all, let's do all the necessary imports from DFF.
"""

# %pip install dff

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
def add_prefix(prefix):
    def add_prefix_processing(ctx: Context, _: Pipeline):
        processed_node = ctx.current_node
        processed_node.response = Message(
            text=f"{prefix}: {processed_node.response.text}"
        )

    return add_prefix_processing


# %% [markdown]
"""
`PRE_RESPONSE_PROCESSING` is a keyword that
can be used in `GLOBAL`, `LOCAL` or nodes.
"""


# %%
toy_script = {
    "root": {
        "start": {
            RESPONSE: Message(),
            TRANSITIONS: {("flow", "step_0"): cnd.true()},
        },
        "fallback": {RESPONSE: Message("the end")},
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
        "step_0": {
            RESPONSE: Message("first"),
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_1": {
            PRE_RESPONSE_PROCESSING: {"proc_name_1": add_prefix("l1_step_1")},
            RESPONSE: Message("second"),
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_2": {
            PRE_RESPONSE_PROCESSING: {"proc_name_2": add_prefix("l2_step_2")},
            RESPONSE: Message("third"),
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_3": {
            PRE_RESPONSE_PROCESSING: {"proc_name_3": add_prefix("l3_step_3")},
            RESPONSE: Message("fourth"),
            TRANSITIONS: {lbl.forward(): cnd.true()},
        },
        "step_4": {
            PRE_RESPONSE_PROCESSING: {"proc_name_4": add_prefix("l4_step_4")},
            RESPONSE: Message("fifth"),
            TRANSITIONS: {"step_0": cnd.true()},
        },
    },
}


# testing
happy_path = (
    (Message(), Message("l3_local: l2_local: l1_global: first")),
    (Message(), Message("l3_local: l2_local: l1_step_1: second")),
    (Message(), Message("l3_local: l2_step_2: l1_global: third")),
    (Message(), Message("l3_step_3: l2_local: l1_global: fourth")),
    (
        Message(),
        Message("l4_step_4: l3_local: l2_local: l1_global: fifth"),
    ),
    (Message(), Message("l3_local: l2_local: l1_global: first")),
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
