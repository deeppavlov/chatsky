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
            TRANSITIONS: {"node1": exact_match(Message("Hi"))},
        },
        "node1": {
            RESPONSE: Message("Hi, how are you?"),
            TRANSITIONS: {"node2": exact_match(Message("i'm fine, how are you?"))},
        },
        "node2": {
            RESPONSE: Message("Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": exact_match(Message("Let's talk about music."))},
        },
        "node3": {
            RESPONSE: Message("Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": exact_match(Message("Ok, goodbye."))},
        },
        "node4": {RESPONSE: Message("bye"), TRANSITIONS: {"node1": exact_match(Message("Hi"))}},
        "fallback_node": {
            RESPONSE: Message("Ooops"),
            TRANSITIONS: {"node1": exact_match(Message("Hi"))},
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
    (Message("Hi"), Message("Hi, how are you?")),
    (Message("i'm fine, how are you?"), Message("Good. What do you want to talk about?")),
    (Message("Let's talk about music."), Message("Sorry, I can not talk about music now.")),
    (Message("Ok, goodbye."), Message("bye")),
    (Message("Hi"), Message("Hi, how are you?")),
)
"""
An example of a simple dialog.

:meta hide-value:
"""

MULTIFLOW_SCRIPT = {
    "root": {
        "start": {
            RESPONSE: Message("Hi"),
            TRANSITIONS: {
                ("small_talk", "ask_some_questions"): exact_match(Message("hi")),
                ("animals", "have_pets"): exact_match(Message("i like animals")),
                ("animals", "like_animals"): exact_match(Message("let's talk about animals")),
                ("news", "what_news"): exact_match(Message("let's talk about news")),
            },
        },
        "fallback": {RESPONSE: Message("Oops")},
    },
    "animals": {
        "have_pets": {
            RESPONSE: Message("do you have pets?"),
            TRANSITIONS: {"what_animal": exact_match(Message("yes"))},
        },
        "like_animals": {
            RESPONSE: Message("do you like it?"),
            TRANSITIONS: {"what_animal": exact_match(Message("yes"))},
        },
        "what_animal": {
            RESPONSE: Message("what animals do you have?"),
            TRANSITIONS: {
                "ask_about_color": exact_match(Message("bird")),
                "ask_about_breed": exact_match(Message("dog")),
            },
        },
        "ask_about_color": {RESPONSE: Message("what color is it")},
        "ask_about_breed": {
            RESPONSE: Message("what is this breed?"),
            TRANSITIONS: {
                "ask_about_breed": exact_match(Message("pereat")),
                "tell_fact_about_breed": exact_match(Message("bulldog")),
                "ask_about_training": exact_match(Message("I don't know")),
            },
        },
        "tell_fact_about_breed": {
            RESPONSE: Message("Bulldogs appeared in England as specialized bull-baiting dogs. "),
        },
        "ask_about_training": {RESPONSE: Message("Do you train your dog? ")},
    },
    "news": {
        "what_news": {
            RESPONSE: Message("what kind of news do you prefer?"),
            TRANSITIONS: {
                "ask_about_science": exact_match(Message("science")),
                "ask_about_sport": exact_match(Message("sport")),
            },
        },
        "ask_about_science": {
            RESPONSE: Message("i got news about science, do you want to hear?"),
            TRANSITIONS: {
                "science_news": exact_match(Message("yes")),
                ("small_talk", "ask_some_questions"): exact_match(Message("let's change the topic")),
            },
        },
        "science_news": {
            RESPONSE: Message("This is science news"),
            TRANSITIONS: {
                "what_news": exact_match(Message("ok")),
                ("small_talk", "ask_some_questions"): exact_match(Message("let's change the topic")),
            },
        },
        "ask_about_sport": {
            RESPONSE: Message("i got news about sport, do you want to hear?"),
            TRANSITIONS: {
                "sport_news": exact_match(Message("yes")),
                ("small_talk", "ask_some_questions"): exact_match(Message("let's change the topic")),
            },
        },
        "sport_news": {
            RESPONSE: Message("This is sport news"),
            TRANSITIONS: {
                "what_news": exact_match(Message("ok")),
                ("small_talk", "ask_some_questions"): exact_match(Message("let's change the topic")),
            },
        },
    },
    "small_talk": {
        "ask_some_questions": {
            RESPONSE: Message("how are you"),
            TRANSITIONS: {
                "ask_talk_about": exact_match(Message("fine")),
                ("animals", "like_animals"): exact_match(Message("let's talk about animals")),
                ("news", "what_news"): exact_match(Message("let's talk about news")),
            },
        },
        "ask_talk_about": {
            RESPONSE: Message("what do you want to talk about"),
            TRANSITIONS: {
                ("animals", "like_animals"): exact_match(Message("dog")),
                ("news", "what_news"): exact_match(Message("let's talk about news")),
            },
        },
    },
}
"""
Simple dialog with multiple flows.

:meta hide-value:
"""

MULTIFLOW_REQUEST_OPTIONS = {
    "root": {
        "start": [
            "hi",
            "i like animals",
            "let's talk about animals",
        ]
    },
    "animals": {
        "have_pets": ["yes"],
        "like_animals": ["yes"],
        "what_animal": ["bird", "dog"],
        "ask_about_breed": ["pereat", "bulldog", "I don't know"],
    },
    "news": {
        "what_news": ["science", "sport"],
        "ask_about_science": ["yes", "let's change the topic"],
        "science_news": ["ok", "let's change the topic"],
        "ask_about_sport": ["yes", "let's change the topic"],
        "sport_news": ["ok", "let's change the topic"],
    },
    "small_talk": {
        "ask_some_questions": [
            "fine",
            "let's talk about animals",
            "let's talk about news",
        ],
        "ask_talk_about": ["dog", "let's talk about news"],
    },
}
"""
Request options for automated client requests for :py:data:`~.MULTIFLOW_SCRIPT`.

:meta hide-value:
"""
