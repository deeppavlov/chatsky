# %% [markdown]
"""
# 1. Basics

The following tutorial shows basic usage of `pipeline`
module as an extension to `dff.script.core`.

Here, `__call__` (same as
%mddoclink(api,pipeline.pipeline.pipeline,Pipeline.run))
method is used to execute pipeline once.
"""

# %pip install dff

# %%
from dff.script import Context, Message

from dff.pipeline import Pipeline

from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    HAPPY_PATH,
    TOY_SCRIPT,
    TOY_SCRIPT_ARGS,
)


# %% [markdown]
"""
`Pipeline` is an object, that automates script execution and context management.
`from_script` method can be used to create
a pipeline of the most basic structure:
"preprocessors -> actor -> postprocessors"
as well as to define `context_storage` and `messenger_interface`.
Actor is a component of :py:class:`.Pipeline`, that contains the
:py:class:`.Script` and handles it. It is responsible for processing
user input and determining the appropriate response based on the
current state of the conversation and the script.
These parameters usage will be shown in tutorials 2, 3 and 6.

Here only required parameters are provided to pipeline.
`context_storage` will default to simple Python dict and
`messenger_interface` will never be used.
pre- and postprocessors lists are empty.
`Pipeline` object can be called with user input
as first argument and dialog id (any immutable object).
This call will return `Context`,
its `last_response` property will be actors response.
"""

# %%
pipeline = Pipeline.from_script(
    TOY_SCRIPT,
    # Pipeline script object, defined in `dff.utils.testing.toy_script`
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)


# %% [markdown]
"""
For the sake of brevity, other tutorials
might use `TOY_SCRIPT_ARGS` to initialize pipeline:
"""

# %%
assert TOY_SCRIPT_ARGS == (
    TOY_SCRIPT,
    ("greeting_flow", "start_node"),
    ("greeting_flow", "fallback_node"),
)


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    # a function for automatic tutorial running (testing) with HAPPY_PATH

    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        ctx_id = 0  # 0 will be current dialog (context) identification.
        while True:
            message = Message(input("Send request: "))
            ctx: Context = pipeline(message, ctx_id)
            print(ctx.last_response)
