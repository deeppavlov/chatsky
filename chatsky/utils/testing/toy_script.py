"""
Toy script
----------
This module contains a simple script and a dialog which are used
in tutorials.
"""

from chatsky.conditions import ExactMatch
from chatsky.core import TRANSITIONS, RESPONSE, Message, Transition as Tr

TOY_SCRIPT = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: [Tr(dst="node1", cnd=ExactMatch("Hi"))],
        },
        "node1": {
            RESPONSE: "Hi, how are you?",
            TRANSITIONS: [Tr(dst="node2", cnd=ExactMatch("i'm fine, how are you?"))],
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: [Tr(dst="node3", cnd=ExactMatch("Let's talk about music."))],
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about music now.",
            TRANSITIONS: [Tr(dst="node4", cnd=ExactMatch("Ok, goodbye."))],
        },
        "node4": {RESPONSE: "bye", TRANSITIONS: [Tr(dst="node1", cnd=ExactMatch("Hi"))]},
        "fallback_node": {
            RESPONSE: "Ooops",
            TRANSITIONS: [Tr(dst="node1", cnd=ExactMatch("Hi"))],
        },
    }
}
"""
An example of a simple script.

:meta hide-value:
"""

TOY_SCRIPT_KWARGS = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
}
"""
# There should be a better description of this
Keyword arguments to pass to :py:meth:`~chatsky.pipeline.pipeline.pipeline.Pipeline` in order to
use :py:data:`~.TOY_SCRIPT`:

.. code-block::

    Pipeline(**TOY_SCRIPT_KWARGS, context_storage=...)

:meta hide-value:
"""

HAPPY_PATH = (
    ("Hi", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),
    ("Hi", "Hi, how are you?"),
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
                ("small_talk", "ask_some_questions"): ExactMatch("hi"),
                ("animals", "have_pets"): ExactMatch("i like animals"),
                ("animals", "like_animals"): ExactMatch("let's talk about animals"),
                ("news", "what_news"): ExactMatch("let's talk about news"),
            },
        },
        "fallback": {RESPONSE: Message("Oops")},
    },
    "animals": {
        "have_pets": {
            RESPONSE: Message("do you have pets?"),
            TRANSITIONS: {"what_animal": ExactMatch("yes")},
        },
        "like_animals": {
            RESPONSE: Message("do you like it?"),
            TRANSITIONS: {"what_animal": ExactMatch("yes")},
        },
        "what_animal": {
            RESPONSE: Message("what animals do you have?"),
            TRANSITIONS: {
                "ask_about_color": ExactMatch("bird"),
                "ask_about_breed": ExactMatch("dog"),
            },
        },
        "ask_about_color": {RESPONSE: Message("what color is it")},
        "ask_about_breed": {
            RESPONSE: Message("what is this breed?"),
            TRANSITIONS: {
                "ask_about_breed": ExactMatch("pereat"),
                "tell_fact_about_breed": ExactMatch("bulldog"),
                "ask_about_training": ExactMatch("I don't know"),
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
                "ask_about_science": ExactMatch("science"),
                "ask_about_sport": ExactMatch("sport"),
            },
        },
        "ask_about_science": {
            RESPONSE: Message("i got news about science, do you want to hear?"),
            TRANSITIONS: {
                "science_news": ExactMatch("yes"),
                ("small_talk", "ask_some_questions"): ExactMatch("let's change the topic"),
            },
        },
        "science_news": {
            RESPONSE: Message("This is science news"),
            TRANSITIONS: {
                "what_news": ExactMatch("ok"),
                ("small_talk", "ask_some_questions"): ExactMatch("let's change the topic"),
            },
        },
        "ask_about_sport": {
            RESPONSE: Message("i got news about sport, do you want to hear?"),
            TRANSITIONS: {
                "sport_news": ExactMatch("yes"),
                ("small_talk", "ask_some_questions"): ExactMatch("let's change the topic"),
            },
        },
        "sport_news": {
            RESPONSE: Message("This is sport news"),
            TRANSITIONS: {
                "what_news": ExactMatch("ok"),
                ("small_talk", "ask_some_questions"): ExactMatch("let's change the topic"),
            },
        },
    },
    "small_talk": {
        "ask_some_questions": {
            RESPONSE: Message("how are you"),
            TRANSITIONS: {
                "ask_talk_about": ExactMatch("fine"),
                ("animals", "like_animals"): ExactMatch("let's talk about animals"),
                ("news", "what_news"): ExactMatch("let's talk about news"),
            },
        },
        "ask_talk_about": {
            RESPONSE: Message("what do you want to talk about"),
            TRANSITIONS: {
                ("animals", "like_animals"): ExactMatch("dog"),
                ("news", "what_news"): ExactMatch("let's talk about news"),
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
