"""
Toy script
----------
This module contains a simple script and a dialog which are used
in tutorials.
"""
from dff.script.conditions import exact_match
from dff.script import TRANSITIONS, RESPONSE, Message

TOY_SCRIPT = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: Message(),
            TRANSITIONS: {"node1": exact_match(Message(text="Hi"))},
        },
        "node1": {
            RESPONSE: Message(text="Hi, how are you?"),
            TRANSITIONS: {"node2": exact_match(Message(text="i'm fine, how are you?"))},
        },
        "node2": {
            RESPONSE: Message(text="Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": exact_match(Message(text="Let's talk about music."))},
        },
        "node3": {
            RESPONSE: Message(text="Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": exact_match(Message(text="Ok, goodbye."))},
        },
        "node4": {RESPONSE: Message(text="bye"), TRANSITIONS: {"node1": exact_match(Message(text="Hi"))}},
        "fallback_node": {
            RESPONSE: Message(text="Ooops"),
            TRANSITIONS: {"node1": exact_match(Message(text="Hi"))},
        },
    }
}
"""
An example of a simple script.

:meta hide-value:
"""

TOY_SCRIPT_ARGS = (TOY_SCRIPT, ("greeting_flow", "start_node"), ("greeting_flow", "fallback_node"))
"""
Arguments to pass to :py:meth:`~dff.pipeline.pipeline.pipeline.Pipeline.from_script` in order to
use :py:data:`~.TOY_SCRIPT`:

.. code-block::

    Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=..., ...)

:meta hide-value:
"""

HAPPY_PATH = (
    (Message(text="Hi"), Message(text="Hi, how are you?")),
    (Message(text="i'm fine, how are you?"), Message(text="Good. What do you want to talk about?")),
    (Message(text="Let's talk about music."), Message(text="Sorry, I can not talk about music now.")),
    (Message(text="Ok, goodbye."), Message(text="bye")),
    (Message(text="Hi"), Message(text="Hi, how are you?")),
)
"""
An example of a simple dialog.

:meta hide-value:
"""
