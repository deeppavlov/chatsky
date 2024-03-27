# %% [markdown]
"""
# Core: 8. Misc

This tutorial shows `MISC` (miscellaneous) keyword usage.

See %mddoclink(api,script.core.keywords,Keywords.MISC)
for more information.

First of all, let's do all the necessary imports from DFF.
"""

# %pip install dff

# %%
from dff.script import (
    GLOBAL,
    LOCAL,
    RESPONSE,
    TRANSITIONS,
    MISC,
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
def custom_response(ctx: Context, _: Pipeline) -> Message:
    if ctx.validation:
        return Message()
    current_node = ctx.current_node
    return Message(
        text=f"ctx.last_label={ctx.last_label}: "
        f"current_node.misc={current_node.misc}"
    )


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
        "step_4": {
            MISC: {"var3": "info_of_step_4"},
            RESPONSE: custom_response,
            TRANSITIONS: {"step_0": cnd.true()},
        },
    },
}


# testing
happy_path = (
    (
        Message(),
        Message(
            text="ctx.last_label=('flow', 'step_0'): current_node.misc="
            "{'var1': 'global_data', "
            "'var2': 'rewrite_by_local', "
            "'var3': 'info_of_step_0'}"
        ),
    ),
    (
        Message(),
        Message(
            text="ctx.last_label=('flow', 'step_1'): current_node.misc="
            "{'var1': 'global_data', "
            "'var2': 'rewrite_by_local', "
            "'var3': 'info_of_step_1'}"
        ),
    ),
    (
        Message(),
        Message(
            text="ctx.last_label=('flow', 'step_2'): current_node.misc="
            "{'var1': 'global_data', "
            "'var2': 'rewrite_by_local', "
            "'var3': 'info_of_step_2'}"
        ),
    ),
    (
        Message(),
        Message(
            text="ctx.last_label=('flow', 'step_3'): current_node.misc="
            "{'var1': 'global_data', "
            "'var2': 'rewrite_by_local', "
            "'var3': 'info_of_step_3'}"
        ),
    ),
    (
        Message(),
        Message(
            text="ctx.last_label=('flow', 'step_4'): current_node.misc="
            "{'var1': 'global_data', "
            "'var2': 'rewrite_by_local', "
            "'var3': 'info_of_step_4'}"
        ),
    ),
    (
        Message(),
        Message(
            text="ctx.last_label=('flow', 'step_0'): current_node.misc="
            "{'var1': 'global_data', "
            "'var2': 'rewrite_by_local', "
            "'var3': 'info_of_step_0'}"
        ),
    ),
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
