import logging

from dff.utils.generics import run_generics_example
from dff.utils.common import create_example_actor

logger = logging.getLogger(__name__)


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

actor = create_example_actor()

if __name__ == "__main__":
    run_generics_example(logger, actor=actor)
