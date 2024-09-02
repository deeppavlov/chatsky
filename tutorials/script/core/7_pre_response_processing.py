# %% [markdown]
"""
# Core: 7. Pre-response processing

Here, %mddoclink(api,core.script,PRE_RESPONSE)
is demonstrated which can be used for
additional context processing before response handlers.
"""

# %pip install chatsky

# %%
from chatsky import (
    GLOBAL,
    LOCAL,
    RESPONSE,
    TRANSITIONS,
    PRE_RESPONSE,
    Context,
    Message,
    MessageInitTypes,
    BaseResponse,
    Transition as Tr,
    Pipeline,
    destinations as dst,
    processing as proc,
)

from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
)


# %% [markdown]
"""
Processing functions have the same signature as
conditions, responses or destinations
except they don't return anything:

.. python:

    class MyProcessing(BaseProcessing):
        async def call(self, ctx: Context) -> None:
            ...


The main way for processing functions to interact with the script
is modifying `ctx.current_node`, which is used by pipeline
to store a copy of the current node in script.
Any of its attributes can be safely edited, and these changes will
only have an effect during the current turn of the current context.
"""


# %% [markdown]
"""
In this tutorial we'll subclass
%mddoclink(api,processing.standard,ModifyResponse)
processing function so that it would modify response
of the current node to include a prefix.
"""


# %%
class AddPrefix(proc.ModifyResponse):
    prefix: str

    def __init__(self, prefix: str):
        # basemodel does not allow positional arguments by default
        super().__init__(prefix=prefix)

    async def modified_response(
        self, original_response: BaseResponse, ctx: Context
    ) -> MessageInitTypes:
        result = await original_response(ctx)

        if result.text is not None:
            result.text = f"{self.prefix}: {result.text}"
        return result


# %% [markdown]
"""
<div class="alert alert-info">

Tip

You can use `ModifyResponse` to catch exceptions in response functions:

.. python:

    class ExceptionHandler(proc.ModifyResponse):
        async def modified_response(self, original_response, ctx):
            try:
                return await original_response(ctx)
            except Exception as exc:
                return str(exc)

</div>
"""


# %%
toy_script = {
    "root": {
        "start": {
            TRANSITIONS: [Tr(dst=("flow", "step_0"))],
        },
        "fallback": {RESPONSE: "the end"},
    },
    GLOBAL: {
        PRE_RESPONSE: {
            "proc_name_1": AddPrefix("l1_global"),
            "proc_name_2": AddPrefix("l2_global"),
        }
    },
    "flow": {
        LOCAL: {
            PRE_RESPONSE: {
                "proc_name_2": AddPrefix("l2_local"),
                "proc_name_3": AddPrefix("l3_local"),
            },
            TRANSITIONS: [Tr(dst=dst.Forward(loop=True))],
        },
        "step_0": {
            RESPONSE: "first",
        },
        "step_1": {
            PRE_RESPONSE: {"proc_name_1": AddPrefix("l1_step_1")},
            RESPONSE: "second",
        },
        "step_2": {
            PRE_RESPONSE: {"proc_name_2": AddPrefix("l2_step_2")},
            RESPONSE: "third",
        },
        "step_3": {
            PRE_RESPONSE: {"proc_name_3": AddPrefix("l3_step_3")},
            RESPONSE: "fourth",
        },
        "step_4": {
            PRE_RESPONSE: {"proc_name_4": AddPrefix("l4_step_4")},
            RESPONSE: "fifth",
        },
    },
}


# testing
happy_path = (
    (Message(), "l3_local: l2_local: l1_global: first"),
    (Message(), "l3_local: l2_local: l1_step_1: second"),
    (Message(), "l3_local: l2_step_2: l1_global: third"),
    (Message(), "l3_step_3: l2_local: l1_global: fourth"),
    (Message(), "l4_step_4: l3_local: l2_local: l1_global: fifth"),
    (Message(), "l3_local: l2_local: l1_global: first"),
)


# %%
pipeline = Pipeline(
    script=toy_script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path, printout=True)
    if is_interactive_mode():
        pipeline.run()
