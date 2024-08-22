# %% [markdown]
"""
# Core: 9. Pre-transition processing

Here, %mddoclink(api,core.script,PRE_TRANSITION)
is demonstrated which can be used for additional context
processing before transitioning to the next step.
"""

# %pip install chatsky

# %%
from chatsky.core import (
    GLOBAL,
    RESPONSE,
    TRANSITIONS,
    PRE_RESPONSE,
    PRE_TRANSITION,
    Context,
    Pipeline,
    BaseProcessing,
    BaseResponse,
    MessageInitTypes,
    Transition as Tr,
)
import chatsky.destinations as dst

from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
)


# %%
class SavePreviousNodeResponse(BaseProcessing):
    async def call(self, ctx: Context) -> None:
        if ctx.current_node.response is not None:
            ctx.misc["previous_node_response"] = ctx.current_node.response
        # This function is called as Pre-transition
        # so current node is going to be the previous one
        # when we reach the Pre-response step


class PrependPreviousNodeResponse(BaseProcessing):
    class CombinedResponse(BaseResponse):
        first: BaseResponse
        second: BaseResponse

        async def call(self, ctx: Context) -> MessageInitTypes:
            first = await self.first(ctx)
            second = await self.second(ctx)
            return f"previous={first.text}: current={second.text}"

    async def call(self, ctx: Context) -> None:
        if ctx.current_node.response is not None:
            previous_node_response = ctx.misc.get("previous_node_response")
            if previous_node_response is not None:
                ctx.current_node.response = self.CombinedResponse(
                    first=previous_node_response,
                    second=ctx.current_node.response,
                )


# %% [markdown]
"""
<div class="alert alert-info">

Note

Previous node can be accessed another way.

Instead of storing the node response in misc,
one can obtain previous label
with `ctx.labels[-2]` and then get the node from the %mddoclink(api,core.script,Script) object:

```python
ctx.pipeline.script.get_inherited_node(ctx.labels[-2])
```

</div>
"""


# %%
# a dialog script
toy_script = {
    "root": {
        "start": {
            TRANSITIONS: [Tr(dst=("flow", "step_0"))],
        },
        "fallback": {RESPONSE: "the end"},
    },
    GLOBAL: {
        PRE_RESPONSE: {"proc_name_1": PrependPreviousNodeResponse()},
        PRE_TRANSITION: {"proc_name_1": SavePreviousNodeResponse()},
        TRANSITIONS: [Tr(dst=dst.Forward(loop=True))],
    },
    "flow": {
        "step_0": {RESPONSE: "first"},
        "step_1": {RESPONSE: "second"},
        "step_2": {RESPONSE: "third"},
        "step_3": {RESPONSE: "fourth"},
        "step_4": {RESPONSE: "fifth"},
    },
}


# testing
happy_path = (
    ("1", "first"),
    ("2", "previous=first: current=second"),
    ("3", "previous=second: current=third"),
    ("4", "previous=third: current=fourth"),
    ("5", "previous=fourth: current=fifth"),
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
