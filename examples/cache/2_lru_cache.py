# %% [markdown]
"""
# 1. Cache

"""


# %%
# pip install dff  # Uncomment this line to install the framework


# %%
from dff.core.engine.conditions import true
from dff.core.engine.core import Context, Actor
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE
from dff.core.engine.labels import repeat
from dff.core.pipeline import Pipeline
from dff.script.utils.singleton_turn_caching import lru_cache
from dff.utils.testing.common import check_happy_path, is_interactive_mode, run_interactive_mode


external_data = {"counter": 0}


#%%
@lru_cache(maxsize=2)
def cached_response(_):
    """
    This function will work exactly the same as the one from previous example with only one exception.
    Only 2 results will be stored;
    when the function will be executed with third arguments set, the least recent result will be deleted.
    """
    external_data["counter"] += 1
    return external_data["counter"]


def response(ctx: Context, _: Actor, *__, **___):
    if ctx.validation:
        return ""
    return f"{cached_response(1)}-{cached_response(2)}-{cached_response(3)}-{cached_response(2)}-{cached_response(1)}"


#%%
toy_script = {"flow": {"node1": {TRANSITIONS: {repeat(): true()}, RESPONSE: response}}}

happy_path = (
    ("", "1-2-3-2-4"),
    ("", "5-6-7-6-8"),
    ("", "9-10-11-10-12"),
)

pipeline = Pipeline.from_script(toy_script, start_label=("flow", "node1"))


#%%
if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
