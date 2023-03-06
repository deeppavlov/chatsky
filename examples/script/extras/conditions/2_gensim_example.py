# %% [markdown]
"""
# 2. Gensim Example

The following example demonstrates how to employ Gensim models
for annotating user phrases.
"""


# %%
import logging

from gensim.models import Word2Vec, KeyedVectors
import gensim.downloader as api

from dff.script import (
    Message,
    RESPONSE,
    PRE_TRANSITIONS_PROCESSING,
    GLOBAL,
    TRANSITIONS,
)
from dff.script import conditions as cnd

from dff.script.extras.conditions.models import GensimMatcher
from dff.script.extras.conditions.dataset import Dataset
from dff.script.extras.conditions import conditions as i_cnd
from dff.pipeline import Pipeline
from dff.messengers.common import CLIMessengerInterface
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
You can use the `api.load` command to handle loading pre-trained vectors for `Gensim`.

The `Word2Vec` model you instantiate should be passed to `Classifier` / `Matcher` on construction.
Then, the model can be used in the script for annotating user input.
"""


# %%
logger = logging.getLogger(__name__)

# load dataset
dataset = Dataset.parse_obj(
    {
        "items": [
            {
                "label": "hello",
                "samples": [
                    "hi",
                    "hello",
                ],
            },
            {
                "label": "consent",
                "samples": [
                    "totally",
                    "yes",
                    "ok",
                    "surely",
                ],
            },
            {
                "label": "animals",
                "samples": [
                    "dog",
                    "cat",
                    "pet",
                    "I like animals",
                ],
            },
            {
                "label": "sport_news",
                "samples": [
                    "sport",
                    "athletics",
                    "world championship",
                ],
            },
            {
                "label": "science_news",
                "samples": [
                    "discovery",
                    "scientific progress",
                    "science",
                ],
            },
        ]
    }
)
# You can also parse static files using the Dataset structure:
# from pathlib import Path
# dataset = Dataset.parse_yaml(Path(__file__).parent.joinpath("data/chitchat.yaml"))

# load model
wv: KeyedVectors = api.load("glove-wiki-gigaword-50")
model = Word2Vec(vector_size=wv.vector_size)
model.wv = wv
gensim_matcher = GensimMatcher(model=model, dataset=dataset, namespace_key="gensim")


# %%
script = {
    GLOBAL: {PRE_TRANSITIONS_PROCESSING: {"annotate": gensim_matcher}},
    "root": {
        "start": {
            RESPONSE: Message(text="Hi"),
            TRANSITIONS: {
                ("small_talk", "ask_some_questions"): cnd.exact_match(Message(text=("hi"))),
                ("animals", "like_animals"): i_cnd.has_cls_label("animals"),
                ("news", "what_news"): cnd.regexp("news|event"),
            },
        },
        "fallback": {
            RESPONSE: Message(text="Oops"),
            TRANSITIONS: {("small_talk", "ask_talk_about"): cnd.true()},
        },
    },
    "animals": {
        "have_pets": {
            RESPONSE: Message(text="do you have pets?"),
            TRANSITIONS: {"what_animal": i_cnd.has_cls_label("consent")},
        },
        "like_animals": {
            RESPONSE: Message(text="do you like it?"),
            TRANSITIONS: {"what_animal": i_cnd.has_cls_label("consent")},
        },
        "what_animal": {
            RESPONSE: Message(text="what animals do you have?"),
            TRANSITIONS: {
                "ask_about_color": cnd.exact_match(Message(text=("bird"))),
                "ask_about_breed": cnd.exact_match(Message(text=("dog"))),
            },
        },
        "ask_about_color": {RESPONSE: Message(text="what color is it")},
        "ask_about_breed": {
            RESPONSE: Message(text="what is this breed?"),
            TRANSITIONS: {
                "ask_about_breed": cnd.exact_match(Message(text=("pereat"))),
                "tell_fact_about_breed": cnd.exact_match(Message(text=("bulldog"))),
                "ask_about_training": cnd.regexp("no idea|n[o']t know"),
            },
        },
        "tell_fact_about_breed": {
            RESPONSE: Message(
                text="Bulldogs appeared in England as specialized bull-baiting dogs. "
            ),
        },
        "ask_about_training": {RESPONSE: Message(text="Do you train your dog? ")},
    },
    "news": {
        "what_news": {
            RESPONSE: Message(text="what kind of news do you prefer?"),
            TRANSITIONS: {
                "ask_about_science": i_cnd.has_cls_label("science_news"),
                "ask_about_sport": i_cnd.has_cls_label("sport_news"),
            },
        },
        "ask_about_science": {
            RESPONSE: Message(text="i got news about science, would you like to hear them?"),
            TRANSITIONS: {
                "science_news": i_cnd.has_cls_label("consent"),
                ("small_talk", "ask_some_questions"): cnd.regexp("change the topic"),
            },
        },
        "science_news": {
            RESPONSE: Message(
                text="The newly discovered comet will be named after DeepPavlov team. More at 11."
            ),
            TRANSITIONS: {
                "what_news": i_cnd.has_cls_label("consent"),
                ("small_talk", "ask_some_questions"): cnd.regexp("change the topic"),
            },
        },
        "ask_about_sport": {
            RESPONSE: Message(text="i got news about sport, do you want to hear?"),
            TRANSITIONS: {
                "sport_news": i_cnd.has_cls_label("consent"),
                ("small_talk", "ask_some_questions"): cnd.regexp("change the topic"),
            },
        },
        "sport_news": {
            RESPONSE: Message(
                text="Did you know that an AI-controlled robot plays soccer better than humans?"
            ),
            TRANSITIONS: {
                "what_news": i_cnd.has_cls_label("consent"),
                ("small_talk", "ask_some_questions"): cnd.regexp("change the topic"),
            },
        },
    },
    "small_talk": {
        "ask_some_questions": {
            RESPONSE: Message(text="how are you"),
            TRANSITIONS: {
                "ask_talk_about": cnd.regexp("fine"),
                ("animals", "like_animals"): i_cnd.has_cls_label("animals"),
                ("news", "what_news"): cnd.regexp("news|event"),
            },
        },
        "ask_talk_about": {
            RESPONSE: Message(text="what do you want to talk about"),
            TRANSITIONS: {
                ("animals", "like_animals"): i_cnd.has_cls_label("animals"),
                ("news", "what_news"): cnd.regexp("news|event"),
            },
        },
    },
}


# %%
happy_path = [
    (Message(text="hi"), Message(text="how are you")),
    (Message(text="fine"), Message(text="what do you want to talk about")),
    (Message(text="news"), Message(text="what kind of news do you prefer?")),
    (
        Message(text="science"),
        Message(text="i got news about science, would you like to hear them?"),
    ),
    (
        Message(text="yes"),
        Message(text="The newly discovered comet will be named after DeepPavlov team. More at 11."),
    ),
    (Message(text="totally"), Message(text="what kind of news do you prefer?")),
    (Message(text="sport"), Message(text="i got news about sport, do you want to hear?")),
]


# %%
pipeline = Pipeline.from_script(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(intro="Starting Dff bot..."),
)


# %%
if __name__ == "__main__" and is_interactive_mode():
    pipeline.run()
