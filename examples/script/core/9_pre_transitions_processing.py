# %% [markdown]
"""
# 9. Pre-transitions processing

This example shows pre-transitions processing feature.
First of all, let's do all the necessary imports from `dff`.
"""


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
def save_previous_node_response_to_ctx_processing(
    ctx: Context, line: Pipeline, *args, **kwargs
) -> Context:
    processed_node = ctx.current_node
    ctx.misc["previous_node_response"] = processed_node.response
    return ctx


def get_previous_node_response_for_response_processing(
    ctx: Context, line: Pipeline, *args, **kwargs
) -> Context:
    processed_node = ctx.current_node
    processed_node.response = Message(
        text=f"previous={ctx.misc['previous_node_response'].text}:"
        f" current={processed_node.response.text}"
    )
    ctx.overwrite_current_node_in_processing(processed_node)
    return ctx


# %%
# a dialog script
toy_script = {
    "root": {
        "start": {RESPONSE: Message(), TRANSITIONS: {("flow", "step_0"): cnd.true()}},
        "fallback": {RESPONSE: Message(text="the end")},
    },
    GLOBAL: {
        PRE_RESPONSE_PROCESSING: {
            "proc_name_1": get_previous_node_response_for_response_processing
        },
        PRE_TRANSITIONS_PROCESSING: {"proc_name_1": save_previous_node_response_to_ctx_processing},
        TRANSITIONS: {lbl.forward(0.1): cnd.true()},
    },
    "flow": {
        "step_0": {RESPONSE: Message(text="first")},
        "step_1": {RESPONSE: Message(text="second")},
        "step_2": {RESPONSE: Message(text="third")},
        "step_3": {RESPONSE: Message(text="fourth")},
        "step_4": {RESPONSE: Message(text="fifth")},
    },
}


# testing
happy_path = (
    (Message(text="1"), Message(text="previous=None: current=first")),
    (Message(text="2"), Message(text="previous=first: current=second")),
    (Message(text="3"), Message(text="previous=second: current=third")),
    (Message(text="4"), Message(text="previous=third: current=fourth")),
    (Message(text="5"), Message(text="previous=fourth: current=fifth")),
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
