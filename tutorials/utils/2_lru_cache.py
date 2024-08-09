# %% [markdown]
"""
# 2. LRU Cache

In this tutorial use of
%mddoclink(api,utils.turn_caching.singleton_turn_caching,lru_cache)
function is demonstrated.

This function is used a lot like `functools.lru_cache` function and
helps by saving results of heavy function execution and avoiding recalculation.

Caches are kept in a library-wide singleton
and are cleared at the end of each turn.

Maximum size parameter limits the amount of function execution results cached.
"""

# %pip install chatsky

# %%
from chatsky.script.conditions import true
from chatsky.script import Context, TRANSITIONS, RESPONSE, Message
from chatsky.script.labels import repeat
from chatsky.pipeline import Pipeline
from chatsky.utils.turn_caching import lru_cache
from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)

external_data = {"counter": 0}


# %%
@lru_cache(maxsize=2)
def cached_response(_):
    """
    This function will work exactly the same as the one from previous
    tutorial with only one exception.
    Only 2 results will be stored;
    when the function will be executed with third arguments set,
    the least recent result will be deleted.
    """
    external_data["counter"] += 1
    return external_data["counter"]


def response(_: Context, __: Pipeline) -> Message:
    return Message(
        text=f"{cached_response(1)}-{cached_response(2)}-{cached_response(3)}-"
        f"{cached_response(2)}-{cached_response(1)}"
    )


# %%
toy_script = {
    "flow": {"node1": {TRANSITIONS: {repeat(): true()}, RESPONSE: response}}
}

happy_path = (
    (Message(), "1-2-3-2-4"),
    (Message(), "5-6-7-6-8"),
    (Message(), "9-10-11-10-12"),
)

pipeline = Pipeline(script=toy_script, start_label=("flow", "node1"))

# %%
if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
