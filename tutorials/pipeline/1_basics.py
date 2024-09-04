# %% [markdown]
"""
# 1. Basics

The following tutorial shows basic usage of `pipeline`
module as an extension to `chatsky.script.core`.

Here, `__call__` (same as
%mddoclink(api,core.pipeline,Pipeline.run))
method is used to execute pipeline once.
"""

# %pip install chatsky

# %%
from chatsky import Pipeline

from chatsky.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    HAPPY_PATH,
    TOY_SCRIPT,
    TOY_SCRIPT_KWARGS,
)


# %% [markdown]
"""
`Pipeline` is an object, that automates script execution and context management.
It's constructor method can be used to create
a pipeline of the most basic structure:
"pre-services -> actor -> post-services"
as well as to define `context_storage` and `messenger_interface`.
Actor is a component of %mddoclink(api,core.pipeline,Pipeline),
that contains the %mddoclink(api,core.script,Script) and handles it.
It is responsible for processing user input and
determining the appropriate response based on the
current state of the conversation and the script.
These parameters usage will be shown in tutorials 2, 3 and 6.

Here only required parameters are provided to pipeline.
`context_storage` will default to simple Python dict and
`messenger_interface` will never be used.
pre- and post-services lists are empty.
`Pipeline` object can be called with user input
as first argument and dialog id (any immutable object).
This call will return `Context`,
its `last_response` property will be actors response.
"""

# %%
pipeline = Pipeline(
    script=TOY_SCRIPT,
    # Pipeline script object, defined in `chatsky.utils.testing.toy_script`
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)


# %% [markdown]
"""
For the sake of brevity, other tutorials
might use `TOY_SCRIPT_KWARGS` (keyword arguments) to initialize pipeline:
"""

# %%
assert TOY_SCRIPT_KWARGS == {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
}


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH, printout=True)
    # a function for automatic tutorial running (testing) with HAPPY_PATH

    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        pipeline.run()
