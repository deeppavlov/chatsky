# %% [markdown]
"""
# Core: 9. Pre-transitions processing

This tutorial shows pre-transitions processing feature.

Here, %mddoclink(api,script.core.keywords,Keywords.PRE_TRANSITIONS_PROCESSING)
is demonstrated which can be used for additional context
processing before transitioning to the next step.

First of all, let's do all the necessary imports from DFF.
"""

# %pip install dff

# %%
from dff.script import (
    GLOBAL,
    RESPONSE,
    TRANSITIONS,
    PRE_RESPONSE_PROCESSING,
    PRE_TRANSITIONS_PROCESSING,
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
def save_previous_node_response(ctx: Context, _: Pipeline):
    processed_node = ctx.current_node
    ctx.misc["previous_node_response"] = processed_node.response


def prepend_previous_node_response(ctx: Context, _: Pipeline):
    processed_node = ctx.current_node
    processed_node.response = Message(
        text=f"previous={ctx.misc['previous_node_response'].text}:"
        f" current={processed_node.response.text}"
    )


# %%
# a dialog script
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
            "proc_name_1": prepend_previous_node_response
        },
        PRE_TRANSITIONS_PROCESSING: {
            "proc_name_1": save_previous_node_response
        },
        TRANSITIONS: {lbl.forward(0.1): cnd.true()},
    },
    "flow": {
        "step_0": {RESPONSE: Message("first")},
        "step_1": {RESPONSE: Message("second")},
        "step_2": {RESPONSE: Message("third")},
        "step_3": {RESPONSE: Message("fourth")},
        "step_4": {RESPONSE: Message("fifth")},
    },
}


# testing
happy_path = (
    (Message("1"), Message("previous=None: current=first")),
    (Message("2"), Message("previous=first: current=second")),
    (Message("3"), Message("previous=second: current=third")),
    (Message("4"), Message("previous=third: current=fourth")),
    (Message("5"), Message("previous=fourth: current=fifth")),
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
