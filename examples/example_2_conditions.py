import logging

from dff.core.keywords import TRANSITIONS, GRAPH, RESPONSE
from dff.core import Actor
from dff.conditions import exact_match


from examples import example_1_basics

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


flows = {
    "greeting_flow": {
        GRAPH: {
            "node0": {
                RESPONSE: "",
                TRANSITIONS: {"node1": exact_match("Hi")},  # If "Hi" == request of user then we make the transition
            },
            "node1": {
                RESPONSE: "Hi, how are you?",  # When the agent goes to node1, we return "Hi, how are you?"
                TRANSITIONS: {"node2": exact_match("i'm fine, how are you?")},
            },
            "node2": {
                RESPONSE: "Good. What do you want to talk about?",
                TRANSITIONS: {"node3": exact_match("Let's talk about music.")},
            },
            "node3": {
                RESPONSE: "Sorry, I can not talk about music now.",
                TRANSITIONS: {"node4": exact_match("Ok, goodbye.")},
            },
            "node4": {
                RESPONSE: "bye",
                TRANSITIONS: {"node1": exact_match("Hi")},
            },
            "fallback_node": {
                RESPONSE: "Ooops",
                TRANSITIONS: {"node1": exact_match("Hi")},
            },
        }
    },
}
actor = Actor(
    flows,
    start_node_label=("greeting_flow", "node0"),
    fallback_node_label=("greeting_flow", "fallback_node"),
)


# testing
testing_dialog = [
    ("Hi", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),
    ("Hi", "Hi, how are you?"),
    ("stop", "Ooops"),
    ("stop", "Ooops"),
    ("Hi", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),
]


def run_test():
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


if __name__ == "__main__":
    run_test()
    example_1_basics.run_interactive_mode(actor)
