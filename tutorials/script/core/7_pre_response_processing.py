# %% [markdown]
"""
# Core: 7. Pre-response processing

Here, %mddoclink(api,core.script,PRE_RESPONSE)
is demonstrated which can be used for
additional context processing before response handlers.
"""

# %pip install chatsky

# %%
from chatsky.core import (
    GLOBAL,
    LOCAL,
    RESPONSE,
    TRANSITIONS,
    PRE_RESPONSE,
    Context,
    Message,
    MessageInitTypes,
    Transition as Tr,
    Pipeline,
    BaseProcessing,
    BaseResponse,
)
import chatsky.destinations as dst

from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
)


# %% [markdown]
"""
Here we define a processing function that will modify the
`response` field of the current node to prefix specific text.
"""


# %%
class AddPrefix(BaseProcessing):
    prefix: str

    def __init__(self, prefix: str):
        # basemodel does not allow positional arguments by default
        super().__init__(prefix=prefix)

    class PrefixedResponse(BaseResponse):
        prefix: str
        base_response: BaseResponse

        async def call(self, ctx: Context) -> MessageInitTypes:
            result = await self.base_response(ctx)
            # get the result of the original response
            if result.text is not None:
                result.text = f"{self.prefix}: {result.text}"
            return result

    async def call(self, ctx: Context) -> None:  # processing has no return
        if ctx.current_node.response is not None:
            ctx.current_node.response = self.PrefixedResponse(
                prefix=self.prefix, base_response=ctx.current_node.response
            )


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
