import logging
import re

from df_engine.core.keywords import TRANSITIONS, RESPONSE
from df_engine.core import Actor, Context
import df_engine.conditions as cnd

from examples import example_1_basics

logger = logging.getLogger(__name__)


# Here we will consider different options for setting transition conditions.

# The transition condition is set by the function.
# If the function returns the value `true`, then the actor performs the corresponding transition.
# Condition functions have signature ```def func(ctx: Context, actor: Actor, *args, **kwargs) -> bool```

# Out of the box, df_engine offers 8 options for setting conditions:
# - `exact_match` - will return `true` if the user's request completely matches the value passed to the function.
# - `regexp` - will return `true` if the pattern matches the user's request, while the user's request must be a string.
# -            `regexp` has same signature as `re.compile` function.
# - `aggregate` - returns bool value as result after aggregate by `aggregate_func` for input sequence of condtions.
#              `aggregate_func` == any by default
#              `aggregate` has alias `agg`
# - `any` - will return `true` if an one element of  input sequence of condtions is `true`
#           any(input_sequence) is equivalent to aggregate(input sequence, aggregate_func=any)
# - `all` - will return `true` if all elements of  input sequence of condtions are `true`
#           all(input_sequence) is equivalent to aggregate(input sequence, aggregate_func=all)
# - `negation` - return a negation of passed function
#              `negation` has alias `neg`
# - `has_last_labels` - covered in the following examples.
# - `true` - returns true
# - `false` - returns false


def hi_lower_case_condition(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    request = ctx.last_request
    return "hi" in request.lower()


def complex_user_answer_condition(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    request = ctx.last_request
    # the user request can be anything
    return {"some_key": "some_value"} == request


def predetermined_condition(condition: bool):
    # wrapper for internal condition function
    def internal_condition_function(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        # It always returns `condition`.
        return condition

    return internal_condition_function


plot = {
    "greeting_flow": {
        "start_node": {  # This is an initial node, it doesn't need an `RESPONSE`
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},  # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: ["Hi, how are you?"],
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

actor = Actor(plot, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))


# testing
testing_dialog = [
    ("Hi", ["Hi, how are you?"]),  # start_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "bye"),  # node3 -> node4
    ("Hi", ["Hi, how are you?"]),  # node4 -> node1
    ("stop", "Ooops"),  # node1 -> fallback_node
    ("one", "Ooops"),  # fallback_node -> fallback_node
    ("help", "Ooops"),  # fallback_node -> fallback_node
    ("nope", "Ooops"),  # fallback_node -> fallback_node
    ({"some_key": "some_value"}, ["Hi, how are you?"]),  # fallback_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "bye"),  # node3 -> node4
]


def run_test():
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s", level=logging.INFO
    )
    # run_test()
    example_1_basics.run_interactive_mode(actor)
