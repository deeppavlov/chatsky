import logging
from pathlib import Path

from gensim.models import Word2Vec, KeyedVectors
import gensim.downloader as api

from dff.core.engine.core.keywords import RESPONSE, PRE_TRANSITIONS_PROCESSING, GLOBAL, TRANSITIONS, LOCAL
from dff.core.engine import conditions as cnd

from dff.script.logic.extended_conditions.models import GensimMatcher
from dff.script.logic.extended_conditions.dataset import Dataset
from dff.script.logic.extended_conditions import conditions as i_cnd
from dff.core.pipeline import Pipeline, CLIMessengerInterface
from dff.utils.testing.common import is_interactive_mode, run_interactive_mode

logger = logging.getLogger(__name__)

# load dataset
data_path = Path(__file__).parent.joinpath("data/chitchat.yaml")
dataset = Dataset.parse_yaml(data_path)
# load model
wv: KeyedVectors = api.load("glove-wiki-gigaword-50")
model = Word2Vec(vector_size=wv.vector_size)
model.wv = wv
gensim_matcher = GensimMatcher(model=model, dataset=dataset, namespace_key="gensim")

script = {
    GLOBAL: {PRE_TRANSITIONS_PROCESSING: {"annotate": gensim_matcher}},
    "root": {
        "start": {
            RESPONSE: "Hi",
            TRANSITIONS: {
                ("small_talk", "ask_some_questions"): cnd.exact_match("hi"),
                ("animals", "like_animals"): i_cnd.has_cls_label("animals"),
                ("news", "what_news"): cnd.regexp("news|event"),
            },
        },
        "fallback": {RESPONSE: "Oops", TRANSITIONS: {("small_talk", "ask_talk_about"): cnd.true()}},
    },
    "animals": {
        "have_pets": {RESPONSE: "do you have pets?", TRANSITIONS: {"what_animal": i_cnd.has_cls_label("consent")}},
        "like_animals": {RESPONSE: "do you like it?", TRANSITIONS: {"what_animal": i_cnd.has_cls_label("consent")}},
        "what_animal": {
            RESPONSE: "what animals do you have?",
            TRANSITIONS: {"ask_about_color": cnd.exact_match("bird"), "ask_about_breed": cnd.exact_match("dog")},
        },
        "ask_about_color": {RESPONSE: "what color is it"},
        "ask_about_breed": {
            RESPONSE: "what is this breed?",
            TRANSITIONS: {
                "ask_about_breed": cnd.exact_match("pereat"),
                "tell_fact_about_breed": cnd.exact_match("bulldog"),
                "ask_about_training": cnd.regexp("no idea|n[o']t know"),
            },
        },
        "tell_fact_about_breed": {
            RESPONSE: "Bulldogs appeared in England as specialized bull-baiting dogs. ",
        },
        "ask_about_training": {RESPONSE: "Do you train your dog? "},
    },
    "news": {
        "what_news": {
            RESPONSE: "what kind of news do you prefer?",
            TRANSITIONS: {
                "ask_about_science": i_cnd.has_cls_label("science_news"),
                "ask_about_sport": i_cnd.has_cls_label("sport_news"),
            },
        },
        "ask_about_science": {
            RESPONSE: "i got news about science, would you like to hear them?",
            TRANSITIONS: {
                "science_news": i_cnd.has_cls_label("consent"),
                ("small_talk", "ask_some_questions"): cnd.regexp("change the topic"),
            },
        },
        "science_news": {
            RESPONSE: "The newly discovered comet is highly likely to be named after DeepPavlov team. More at 11.",
            TRANSITIONS: {
                "what_news": i_cnd.has_cls_label("consent"),
                ("small_talk", "ask_some_questions"): cnd.regexp("change the topic"),
            },
        },
        "ask_about_sport": {
            RESPONSE: "i got news about sport, do you want to hear?",
            TRANSITIONS: {
                "sport_news": i_cnd.has_cls_label("consent"),
                ("small_talk", "ask_some_questions"): cnd.regexp("change the topic"),
            },
        },
        "sport_news": {
            RESPONSE: "Did you know that an AI-controlled robot plays soccer better than every coworker at DeepPavlov?",
            TRANSITIONS: {
                "what_news": i_cnd.has_cls_label("consent"),
                ("small_talk", "ask_some_questions"): cnd.regexp("change the topic"),
            },
        },
    },
    "small_talk": {
        "ask_some_questions": {
            RESPONSE: "how are you",
            TRANSITIONS: {
                "ask_talk_about": cnd.regexp("fine"),
                ("animals", "like_animals"): i_cnd.has_cls_label("animals"),
                ("news", "what_news"): cnd.regexp("news|event"),
            },
        },
        "ask_talk_about": {
            RESPONSE: "what do you want to talk about",
            TRANSITIONS: {
                ("animals", "like_animals"): i_cnd.has_cls_label("animals"),
                ("news", "what_news"): cnd.regexp("news|event"),
            },
        },
    },
}

happy_path = [
    ("hi", "how are you"),
    ("fine", "what do you want to talk about"),
    ("news", "what kind of news do you prefer?"),
    ("science", "i got news about science, would you like to hear them?"),
    ("yeah", "The newly discovered comet is highly likely to be named after DeepPavlov team. More at 11."),
    ("totally", "what kind of news do you prefer?"),
    ("sport", "i got news about sport, do you want to hear?"),
]

pipeline = Pipeline.from_script(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(intro="Starting Dff bot..."),
)


def main():
    if is_interactive_mode():
        run_interactive_mode(pipeline)
    else:
        pipeline.run()


if __name__ == "__main__":
    main()
