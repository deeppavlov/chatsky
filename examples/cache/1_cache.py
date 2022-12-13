# %% [markdown]
"""
# 1. Cache

"""


# %%
from dff.core.engine.conditions import true
from dff.core.engine.core import Context, Actor
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE
from dff.core.engine.labels import repeat
from dff.core.pipeline import Pipeline
from dff.script.utils.singleton_turn_caching import cache
from dff.utils.testing.common import (
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


def response(ctx: Context, _: Actor, *__, **___):
    if ctx.validation:
        return ""
    return (
        f"{cached_response(1)}-{cached_response(2)}-" f"{cached_response(1)}-{cached_response(2)}"
    )


# %%
toy_script = {"flow": {"node1": {TRANSITIONS: {repeat(): true()}, RESPONSE: response}}}

happy_path = (
    ("", "1-2-1-2"),
    ("", "3-4-3-4"),
    ("", "5-6-5-6"),
)

pipeline = Pipeline.from_script(toy_script, start_label=("flow", "node1"))


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
