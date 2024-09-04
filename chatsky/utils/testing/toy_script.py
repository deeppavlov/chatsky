"""
Toy script
----------
This module contains a simple script and a dialog which are used
in tutorials.
"""

from chatsky.conditions import ExactMatch
from chatsky.core import TRANSITIONS, RESPONSE, Transition as Tr

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
Keyword arguments to pass to :py:meth:`~chatsky.core.pipeline.Pipeline` in order to
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
            RESPONSE: "Hi",
            TRANSITIONS: [
                Tr(dst=("small_talk", "ask_some_questions"), cnd=ExactMatch("hi")),
                Tr(dst=("animals", "have_pets"), cnd=ExactMatch("i like animals")),
                Tr(dst=("animals", "like_animals"), cnd=ExactMatch("let's talk about animals")),
                Tr(dst=("news", "what_news"), cnd=ExactMatch("let's talk about news")),
            ],
        },
        "fallback": {RESPONSE: "Oops", TRANSITIONS: [Tr(dst="start")]},
    },
    "animals": {
        "have_pets": {
            RESPONSE: "do you have pets?",
            TRANSITIONS: [Tr(dst="what_animal", cnd=ExactMatch("yes"))],
        },
        "like_animals": {
            RESPONSE: "do you like it?",
            TRANSITIONS: [Tr(dst="what_animal", cnd=ExactMatch("yes"))],
        },
        "what_animal": {
            RESPONSE: "what animals do you have?",
            TRANSITIONS: [
                Tr(dst="ask_about_color", cnd=ExactMatch("bird")),
                Tr(dst="ask_about_breed", cnd=ExactMatch("dog")),
            ],
        },
        "ask_about_color": {RESPONSE: "what color is it"},
        "ask_about_breed": {
            RESPONSE: "what is this breed?",
            TRANSITIONS: [
                Tr(dst="ask_about_breed", cnd=ExactMatch("pereat")),
                Tr(dst="tell_fact_about_breed", cnd=ExactMatch("bulldog")),
                Tr(dst="ask_about_training", cnd=ExactMatch("I don't know")),
            ],
        },
        "tell_fact_about_breed": {
            RESPONSE: "Bulldogs appeared in England as specialized bull-baiting dogs. ",
        },
        "ask_about_training": {RESPONSE: "Do you train your dog? "},
    },
    "news": {
        "what_news": {
            RESPONSE: "what kind of news do you prefer?",
            TRANSITIONS: [
                Tr(dst="ask_about_science", cnd=ExactMatch("science")),
                Tr(dst="ask_about_sport", cnd=ExactMatch("sport")),
            ],
        },
        "ask_about_science": {
            RESPONSE: "i got news about science, do you want to hear?",
            TRANSITIONS: [
                Tr(dst="science_news", cnd=ExactMatch("yes")),
                Tr(dst=("small_talk", "ask_some_questions"), cnd=ExactMatch("let's change the topic")),
            ],
        },
        "science_news": {
            RESPONSE: "This is science news",
            TRANSITIONS: [
                Tr(dst="what_news", cnd=ExactMatch("ok")),
                Tr(dst=("small_talk", "ask_some_questions"), cnd=ExactMatch("let's change the topic")),
            ],
        },
        "ask_about_sport": {
            RESPONSE: "i got news about sport, do you want to hear?",
            TRANSITIONS: [
                Tr(dst="sport_news", cnd=ExactMatch("yes")),
                Tr(dst=("small_talk", "ask_some_questions"), cnd=ExactMatch("let's change the topic")),
            ],
        },
        "sport_news": {
            RESPONSE: "This is sport news",
            TRANSITIONS: [
                Tr(dst="what_news", cnd=ExactMatch("ok")),
                Tr(dst=("small_talk", "ask_some_questions"), cnd=ExactMatch("let's change the topic")),
            ],
        },
    },
    "small_talk": {
        "ask_some_questions": {
            RESPONSE: "how are you",
            TRANSITIONS: [
                Tr(dst="ask_talk_about", cnd=ExactMatch("fine")),
                Tr(dst=("animals", "like_animals"), cnd=ExactMatch("let's talk about animals")),
                Tr(dst=("news", "what_news"), cnd=ExactMatch("let's talk about news")),
            ],
        },
        "ask_talk_about": {
            RESPONSE: "what do you want to talk about",
            TRANSITIONS: [
                Tr(dst=("animals", "like_animals"), cnd=ExactMatch("dog")),
                Tr(dst=("news", "what_news"), cnd=ExactMatch("let's talk about news")),
            ],
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
        ],
        "fallback": [
            "to start",
        ],
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
