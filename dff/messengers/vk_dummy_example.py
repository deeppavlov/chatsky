from vk import PollingVKInterface
from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.script import Message
from dff.script.conditions import exact_match
from dff.script import RESPONSE, TRANSITIONS
from dff.pipeline import Pipeline


toy_script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: Message(text=""),
            TRANSITIONS: {"node1": exact_match(Message(text="Hi"))},
        },
        "node1": {
            RESPONSE: Message(text="Hi, how are you?"),
            TRANSITIONS: {
                "node2": exact_match(Message(text="i'm fine, how are you?"))
            },
        },
        "node2": {
            RESPONSE: Message(text="Good. What do you want to talk about?"),
            TRANSITIONS: {
                "node3": exact_match(Message(text="Let's talk about music."))
            },
        },
        "node3": {
            RESPONSE: Message(text="Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": exact_match(Message(text="Ok, goodbye."))},
        },
        "node4": {
            RESPONSE: Message(text="bye"),
            TRANSITIONS: {"node1": exact_match(Message(text="Hi"))},
        },
        "fallback_node": {
            RESPONSE: Message(text="Ooops"),
            TRANSITIONS: {"node1": exact_match(Message(text="Hi"))},
        },
    }
}

happy_path = (
    (Message(text="Hi"), Message(text="Hi, how are you?")),
    (
        Message(text="i'm fine, how are you?"),
        Message(text="Good. What do you want to talk about?"),
    ),
    (
        Message(text="Let's talk about music."),
        Message(text="Sorry, I can not talk about music now."),
    ),
    (Message(text="Ok, goodbye."), Message(text="bye")),
    (Message(text="Hi"), Message(text="Hi, how are you?")),
    (Message(text="stop"), Message(text="Ooops")),
    (Message(text="stop"), Message(text="Ooops")),
    (Message(text="Hi"), Message(text="Hi, how are you?")),
    (
        Message(text="i'm fine, how are you?"),
        Message(text="Good. What do you want to talk about?"),
    ),
    (
        Message(text="Let's talk about music."),
        Message(text="Sorry, I can not talk about music now."),
    ),
    (Message(text="Ok, goodbye."), Message(text="bye")),
)

test_dialogue = []

test_interface = PollingVKInterface("token", "id", debug=True, test_path=happy_path)

pipeline = Pipeline.from_script(
    script=toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=test_interface
)

def main():
    pipeline.run()
