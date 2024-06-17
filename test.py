from dff.script import TRANSITIONS, RESPONSE, Message
from dff.pipeline import Pipeline
import dff.script.conditions as cnd

from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)

toy_script = {
    "greeting_flow": {
        "start_node": {  # This is the initial node,
            # it doesn't contain a `RESPONSE`.
            RESPONSE: Message(),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
            # If "Hi" == request of the user then we make the transition.
        },
        "node1": {
            RESPONSE: Message(
                text="Hi, how are you?"
            ),  # When the agent enters node1,
            # return "Hi, how are you?".
            TRANSITIONS: {
                "node2": cnd.exact_match(Message("I'm fine, how are you?"))
            },
        },
        "node2": {
            RESPONSE: Message("Good. What do you want to talk about?"),
            TRANSITIONS: {
                "node3": cnd.exact_match(Message("Let's talk about music."))
            },
        },
        "node3": {
            RESPONSE: Message("Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": cnd.exact_match(Message("Ok, goodbye."))},
        },
        "node4": {
            RESPONSE: Message("Bye"),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
        },
        "fallback_node": {
            # We get to this node if the conditions
            # for switching to other nodes are not performed.
            RESPONSE: Message("Ooops"),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
        },
    }
}


happy_path = (
    (
        Message("Hi"),
        Message("Hi, how are you?"),
    ),  # start_node -> node1
    (
        Message("I'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message("Ok, goodbye."), Message("Bye")),  # node3 -> node4
    (Message("Hi"), Message("Hi, how are you?")),  # node4 -> node1
    (Message("stop"), Message("Ooops")),  # node1 -> fallback_node
    (
        Message("stop"),
        Message("Ooops"),
    ),  # fallback_node -> fallback_node
    (
        Message("Hi"),
        Message("Hi, how are you?"),
    ),  # fallback_node -> node1
    (
        Message("I'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message("Ok, goodbye."), Message("Bye")),  # node3 -> node4
)

pipeline = Pipeline.from_script(
    toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

if __name__ == "__main__":
    check_happy_path(
        pipeline,
        happy_path,
    )  # This is a function for automatic tutorial
    # running (testing tutorial) with `happy_path`.

    # Run tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set.
    if is_interactive_mode():
        run_interactive_mode(pipeline)
        # This runs tutorial in interactive mode.