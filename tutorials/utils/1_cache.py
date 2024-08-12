# %% [markdown]
"""
# 1. Cache

In this tutorial use of
%mddoclink(api,utils.turn_caching.singleton_turn_caching,cache)
function is demonstrated.

This function is used a lot like `functools.cache` function and
helps by saving results of heavy function execution and avoiding recalculation.

Caches are kept in a library-wide singleton
and are cleared at the end of each turn.
"""

# %pip install chatsky

# %%
from chatsky.script.conditions import true
from chatsky.script import Context, TRANSITIONS, RESPONSE, Message
from chatsky.script.labels import repeat
from chatsky.pipeline import Pipeline
from chatsky.utils.turn_caching import cache
from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)


external_data = {"counter": 0}


# %%
@cache
def cached_response(_):
    """
    This function execution result will be saved
    for any set of given argument(s).
    If the function will be called again
    with the same arguments it will prevent it from execution.
    The cached values will be used instead.
    The cache is stored in a library-wide singleton,
    that is cleared in the end of execution of actor and/or pipeline.
    """
    external_data["counter"] += 1
    return external_data["counter"]


def response(_: Context, __: Pipeline) -> Message:
    return Message(
        text=f"{cached_response(1)}-{cached_response(2)}-"
        f"{cached_response(1)}-{cached_response(2)}"
    )


# %%
toy_script = {
    "flow": {"node1": {TRANSITIONS: {repeat(): true()}, RESPONSE: response}}
}

happy_path = (
    (Message(), "1-2-1-2"),
    (Message(), "3-4-3-4"),
    (Message(), "5-6-5-6"),
)

pipeline = Pipeline(script=toy_script, start_label=("flow", "node1"))


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
