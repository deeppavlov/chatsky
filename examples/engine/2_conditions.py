# %% [markdown]
2. Conditions
===============

This example shows different options for setting transition conditions from one node to another.

# %%
import re # Regular expression library

from dff.core.engine.core import Actor, Context
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE
import dff.core.engine.conditions as cnd
from dff.core.pipeline import Pipeline

from dff.utils.testing.common import check_happy_path, is_interactive_mode, run_interactive_mode

# %% [markdown]
The transition condition is set by the function.
If this function returns the value `true`, then the actor performs the corresponding transition.
Condition functions have signature  

    def func(ctx: Context, actor: Actor, *args, **kwargs) -> bool

Out of the box `dff.core.engine` offers 8 options for setting conditions:

* `exact_match` returns `true` if the user's request completely matches the value passed to the function.
* `regexp` returns `true` if the pattern matches the user's request, while the user's request must be a string.
`regexp` has same signature as `re.compile` function.
* `aggregate` returns `bool` value as a result after aggregate by `aggregate_func` for input sequence of condtions.  
`aggregate_func == any` by default. `aggregate` has alias `agg`.
* `any` returns `true` if one element of input sequence of condtions is `true`.
`any(input_sequence)` is equivalent to `aggregate(input sequence, aggregate_func=any)`.
* `all` returns `true` if all elements of input sequence of condtions are `true`.
`all(input_sequence)` is equivalent to `aggregate(input sequence, aggregate_func=all)`.
* `negation` returns negation of passed function. `negation` has alias `neg`.
* `has_last_labels` covered in the following examples.
* `true` returns `true`.
* `false` returns `false`.

For example function
```
def always_true_condition(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True
```
always returns `true` and `always_true_condition` function is same as `dff.core.engine.conditions.true()`.

# %%
def hi_lower_case_condition(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    request = ctx.last_request
    return "hi" in request.lower()


def complex_user_answer_condition(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    request = ctx.last_request
    # The user request can be anything.
    return {"some_key": "some_value"} == request


def predetermined_condition(condition: bool):
    # Wrapper for internal condition function.
    def internal_condition_function(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        # It always returns `condition`.
        return condition

    return internal_condition_function

# %%
toy_script = {
    "greeting_flow": {
        "start_node": {  # This is the initial node, it doesn't contain an `RESPONSE`
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},  # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: "Hi, how are you?",
            TRANSITIONS: {"node2": cnd.regexp(r".*how are you", re.IGNORECASE)},  # pattern matching (precompiled)
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": cnd.all([cnd.regexp(r"talk"), cnd.regexp(r"about.*music")])},
            # mix sequence of condtions by cond.all
            # all is alias `aggregate` with `aggregate_func` == `all`
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about music now.",
            TRANSITIONS: {"node4": cnd.regexp(re.compile(r"Ok, goodbye."))},  # pattern matching by precompiled pattern
        },
        "node4": {
            RESPONSE: "bye",
            TRANSITIONS: {"node1": cnd.any([hi_lower_case_condition, cnd.exact_match("hello")])},
            # mix sequence of condtions by cond.any
            # any is alias `aggregate` with `aggregate_func` == `any`
        },
        "fallback_node": {  # We get to this node if an error occurred while the agent was running
            RESPONSE: "Ooops",
            TRANSITIONS: {
                "node1": complex_user_answer_condition,  # the user request can be more than just a string
                # first we will chech returned value of `complex_user_answer_condition`
                # if the value is True then we will go to `node1`
                # if the value is False then
                # we will check a result of `predetermined_condition(True)` for `fallback_node`
                "fallback_node": predetermined_condition(True),  # or you can use cnd.true()
                # last condition function will return true and will repeat fallback_node
                # if complex_user_answer_condition return false
            },
        },
    }
}

# testing
happy_path = (
    ("Hi", "Hi, how are you?"),  # start_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "bye"),  # node3 -> node4
    ("Hi", "Hi, how are you?"),  # node4 -> node1
    ("stop", "Ooops"),  # node1 -> fallback_node
    ("one", "Ooops"),  # fallback_node -> fallback_node
    ("help", "Ooops"),  # fallback_node -> fallback_node
    ("nope", "Ooops"),  # fallback_node -> fallback_node
    ({"some_key": "some_value"}, "Hi, how are you?"),  # fallback_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "bye"),  # node3 -> node4
)

# %%
pipeline = Pipeline.from_script(
    toy_script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node")
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
