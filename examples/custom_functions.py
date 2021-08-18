import logging

from dff.core.keywords import TRANSITIONS, GRAPH, RESPONSE
from dff.core import Context, Actor

from examples import example_1_basics

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)


# There are two types of custom functions covered here.
# All custom functions have current signature ```def func(ctx: Context, actor: Actor, *args, **kwargs) -> ...```

# The first type of custom functions is condition functions and they return true/false.
# Condition functions have signature ```def func(ctx: Context, actor: Actor, *args, **kwargs) -> bool```


def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    # This is a custom contition function. It always returns true.
    return True


def condition_wrapper(keyword):
    # This is a wrapper of a contition function. It uses ```keyword``` to setup a custom function.
    def cond(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        # if the input phrase contains the keyword then the function will return true else false
        return keyword in ctx.last_request

    return cond


# The second type of custom functions is response functions.
# Response functions have signature ```def func(ctx: Context, actor: Actor, *args, **kwargs) -> Any```
def repeater(ctx: Context, actor: Actor, *args, **kwargs) -> str:
    return f"repeat: {ctx.last_request}"


# This dialog graph consists of two flows (start_flow and repeat_flow)
# The first start_flow is looped using the always_true function.
# But from start_flow you can go to repeat_flow if the user passes the phrase with the keyword = `repeat`
# The second repeat_flow is also looped and will always return the user's phrase with a prefix `repeat: `
flows = {
    "start_flow": {
        GRAPH: {
            "start_node": {
                RESPONSE: "nope",
                TRANSITIONS: {
                    ("repeat_flow", "repeat_node"): condition_wrapper("repeat"),
                    ("start_flow", "start_node"): always_true,
                },
            }
        },
    },
    "repeat_flow": {
        GRAPH: {
            "repeat_node": {
                RESPONSE: repeater,
                TRANSITIONS: {("repeat_flow", "repeat_node"): always_true},
            }
        },
    },
}


actor = Actor(flows, start_node_label=("start_flow", "start_node"))


testing_dialog = [
    ("hi", "nope"),
    ("repeat", "repeat: repeat"),
    ("how are you?", "repeat: how are you?"),
    ("ok", "repeat: ok"),
    ("good", "repeat: good"),
]


def run_test():
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


if __name__ == "__main__":
    run_test()
    example_1_basics.run_interactive_mode(actor)
