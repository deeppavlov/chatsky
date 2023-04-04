# %% [markdown]
"""
# 2. LRU Cache

"""

# %%
from dff.script.conditions import true
from dff.script import Context, Actor, TRANSITIONS, RESPONSE, Message
from dff.script.labels import repeat
from dff.pipeline import Pipeline
from dff.utils.turn_caching import lru_cache
from dff.utils.testing.common import (
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


def response(ctx: Context, _: Actor, *__, **___) -> Message:
    if ctx.validation:
        return Message()
    return Message(
        text=f"{cached_response(1)}-{cached_response(2)}-{cached_response(3)}-"
        f"{cached_response(2)}-{cached_response(1)}"
    )


# %%
toy_script = {"flow": {"node1": {TRANSITIONS: {repeat(): true()}, RESPONSE: response}}}

happy_path = (
    (Message(), Message(text="1-2-3-2-4")),
    (Message(), Message(text="5-6-7-6-8")),
    (Message(), Message(text="9-10-11-10-12")),
)

pipeline = Pipeline.from_script(toy_script, start_label=("flow", "node1"))

# %%
if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
