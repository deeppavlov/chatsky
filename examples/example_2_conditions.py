import logging
import re

from dff.core.keywords import TRANSITIONS, GRAPH, RESPONSE
from dff.core import Actor, Context
from dff.conditions import exact_match, regexp, reduce


from examples import example_1_basics

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# Here we will consider different options for setting transition conditions.

# The transition condition is set by the function.
# If the function returns the value `True`, then the actor performs the corresponding transition.
# Condition functions have signature ```def func(ctx: Context, actor: Actor, *args, **kwargs) -> bool```

# Out of the box, dff offers 3 options for setting conditions:
# - `exact_match` - will return true if the user's request completely matches the value passed to the function.
# - `regexp` - will return true if the pattern matches the user's request, while the user's request must be a string.
# -            `regexp` has same signature as `re.compile` function.
# - `reduce` - returns bool value as result after reduce by `reduce_func` for input sequence of condtions.
#              `reduce_func` == any by default


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


flows = {
    "greeting_flow": {
        GRAPH: {
            "start_node": {  # This is an initial node, it doesn't need an `RESPONSE`
                RESPONSE: "",
                TRANSITIONS: {"node1": exact_match("Hi")},  # If "Hi" == request of user then we make the transition
            },
            "node1": {
                RESPONSE: "Hi, how are you?",
                TRANSITIONS: {"node2": regexp(r".*how are you", re.IGNORECASE)},  # pattern matching
            },
            "node2": {
                RESPONSE: "Good. What do you want to talk about?",
                TRANSITIONS: {"node3": reduce([regexp(r"talk"), regexp(r"about.*music")], reduce_func=all)},
                # mix sequence of condtions by `reduce`, reassignment `reduce_func` by `all`
                # because `reduce_func` == any by default
            },
            "node3": {
                RESPONSE: "Sorry, I can not talk about music now.",
                TRANSITIONS: {"node4": regexp(re.compile(r"Ok, goodbye."))},  # pattern matching by precompiled pattern
            },
            "node4": {
                RESPONSE: "bye",
                TRANSITIONS: {"node1": reduce([hi_lower_case_condition, exact_match("hello")])},
                # mix sequence of condtions by `reduce`, `reduce_func` == any by default
                # because `reduce_func` == any by default
            },
            "fallback_node": {  # We get to this node if an error occurred while the agent was running
                RESPONSE: "Ooops",
                TRANSITIONS: {
                    "node1": complex_user_answer_condition,  # the user request can be more than just a string
                    # first we will chech returned value of `complex_user_answer_condition`
                    # if the value is True then we will go to `node1`
                    # if the value is False then
                    # we will check a result of `predetermined_condition(True)` for `fallback_node`
                    "fallback_node": predetermined_condition(True),
                    # last condition function will return true and will repeat fallback_node
                    # if complex_user_answer_condition return false
                },
            },
        }
    },
}
actor = Actor(
    flows,
    start_node_label=("greeting_flow", "start_node"),
    fallback_node_label=("greeting_flow", "fallback_node"),
)


# testing
testing_dialog = [
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
]


def run_test():
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


if __name__ == "__main__":
    run_test()
    example_1_basics.run_interactive_mode(actor)
