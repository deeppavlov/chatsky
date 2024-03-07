# %% [markdown]
"""
# Core: 2. Conditions

This tutorial shows different options for
setting transition conditions from one node to another.

Here, [conditions](%doclink(api,script.conditions.std_conditions))
for script transitions are shown.

First of all, let's do all the necessary imports from DFF.
"""

# %pip install dff

# %%
import re

from dff.script import Context, TRANSITIONS, RESPONSE, Message
import dff.script.conditions as cnd
from dff.pipeline import Pipeline

from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)

# %% [markdown]
"""
The transition condition is set by the function.
If this function returns the value `True`,
then the actor performs the corresponding transition.
Actor is responsible for processing user input and determining the appropriate
response based on the current state of the conversation and the script.
See tutorial 1 of pipeline (pipeline/1_basics) to learn more about Actor.
Condition functions have signature

    def func(ctx: Context, pipeline: Pipeline) -> bool

Out of the box `dff.script.conditions` offers the
    following options for setting conditions:

* `exact_match` returns `True` if the user's request completely
    matches the value passed to the function.
* `regexp` returns `True` if the pattern matches the user's request,
    while the user's request must be a string.
    `regexp` has same signature as `re.compile` function.
* `aggregate` returns `bool` value as
    a result after aggregate by `aggregate_func`
    for input sequence of conditions.
    `aggregate_func == any` by default. `aggregate` has alias `agg`.
* `any` returns `True` if one element of input sequence of conditions is `True`.
    `any(input_sequence)` is equivalent to
    `aggregate(input sequence, aggregate_func=any)`.
* `all` returns `True` if all elements of input
    sequence of conditions are `True`.
    `all(input_sequence)` is equivalent to
    `aggregate(input sequence, aggregate_func=all)`.
* `negation` returns negation of passed function. `negation` has alias `neg`.
* `has_last_labels` covered in the following examples.
* `true` returns `True`.
* `false` returns `False`.

For example function
```
def always_true_condition(ctx: Context, pipeline: Pipeline) -> bool:
    return True
```
always returns `True` and `always_true_condition` function
is the same as `dff.script.conditions.std_conditions.true()`.

The functions to be used in the `toy_script` are declared here.
"""


# %%
def hi_lower_case_condition(ctx: Context, _: Pipeline) -> bool:
    request = ctx.last_request
    # Returns True if `hi` in both uppercase and lowercase
    # letters is contained in the user request.
    if request is None or request.text is None:
        return False
    return "hi" in request.text.lower()


def complex_user_answer_condition(ctx: Context, _: Pipeline) -> bool:
    request = ctx.last_request
    # The user request can be anything.
    if request is None or request.misc is None:
        return False
    return {"some_key": "some_value"} == request.misc


def predetermined_condition(condition: bool):
    # Wrapper for internal condition function.
    def internal_condition_function(ctx: Context, _: Pipeline) -> bool:
        # It always returns `condition`.
        return condition

    return internal_condition_function


# %%
toy_script = {
    "greeting_flow": {
        "start_node": {  # This is the initial node,
            # it doesn't contain a `RESPONSE`.
            RESPONSE: Message(),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
            # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: Message("Hi, how are you?"),
            TRANSITIONS: {"node2": cnd.regexp(r".*how are you", re.IGNORECASE)},
            # pattern matching (precompiled)
        },
        "node2": {
            RESPONSE: Message("Good. What do you want to talk about?"),
            TRANSITIONS: {
                "node3": cnd.all(
                    [cnd.regexp(r"talk"), cnd.regexp(r"about.*music")]
                )
            },
            # Mix sequence of conditions by `cnd.all`.
            # `all` is alias `aggregate` with
            # `aggregate_func` == `all`.
        },
        "node3": {
            RESPONSE: Message("Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": cnd.regexp(re.compile(r"Ok, goodbye."))},
            # pattern matching by precompiled pattern
        },
        "node4": {
            RESPONSE: Message("bye"),
            TRANSITIONS: {
                "node1": cnd.any(
                    [
                        hi_lower_case_condition,
                        cnd.exact_match(Message("hello")),
                    ]
                )
            },
            # Mix sequence of conditions by `cnd.any`.
            # `any` is alias `aggregate` with
            # `aggregate_func` == `any`.
        },
        "fallback_node": {  # We get to this node
            # if an error occurred while the agent was running.
            RESPONSE: Message("Ooops"),
            TRANSITIONS: {
                "node1": complex_user_answer_condition,
                # The user request can be more than just a string.
                # First we will check returned value of
                # `complex_user_answer_condition`.
                # If the value is `True` then we will go to `node1`.
                # If the value is `False` then we will check a result of
                # `predetermined_condition(True)` for `fallback_node`.
                "fallback_node": predetermined_condition(
                    True
                ),  # or you can use `cnd.true()`
                # Last condition function will return
                # `true` and will repeat `fallback_node`
                # if `complex_user_answer_condition` return `false`.
            },
        },
    }
}

# testing
happy_path = (
    (
        Message("Hi"),
        Message("Hi, how are you?"),
    ),  # start_node -> node1
    (
        Message("i'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message("Ok, goodbye."), Message("bye")),  # node3 -> node4
    (Message("Hi"), Message("Hi, how are you?")),  # node4 -> node1
    (Message("stop"), Message("Ooops")),  # node1 -> fallback_node
    (
        Message("one"),
        Message("Ooops"),
    ),  # fallback_node -> fallback_node
    (
        Message("help"),
        Message("Ooops"),
    ),  # fallback_node -> fallback_node
    (
        Message("nope"),
        Message("Ooops"),
    ),  # fallback_node -> fallback_node
    (
        Message(misc={"some_key": "some_value"}),
        Message("Hi, how are you?"),
    ),  # fallback_node -> node1
    (
        Message("i'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message("Ok, goodbye."), Message("bye")),  # node3 -> node4
)

# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
