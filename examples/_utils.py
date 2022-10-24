import argparse
import sys

from df_engine.core.keywords import RESPONSE, TRANSITIONS
import df_engine.conditions as cnd
from omegaconf import OmegaConf

common_opts = argparse.ArgumentParser(add_help=False)
common_opts.add_argument("-dP", "--db.password", required=True)

parser = argparse.ArgumentParser(
    usage="To run this example, provide the database credentials, using one of the commands below."
)
subparsers = parser.add_subparsers(dest="cmd", description="Configuration source", required=True)
opts_parser = subparsers.add_parser("cfg_from_opts", parents=[common_opts])
opts_parser.add_argument("-dT", "--db.type", choices=["postgresql", "clickhouse"], required=True)
opts_parser.add_argument("-dU", "--db.user", required=True)
opts_parser.add_argument("-dh", "--db.host", required=True)
opts_parser.add_argument("-dp", "--db.port", required=True)
opts_parser.add_argument("-dn", "--db.name", required=True)
opts_parser.add_argument("-dt", "--db.table", required=True)
file_parser = subparsers.add_parser("cfg_from_file", parents=[common_opts])
file_parser.add_argument("file", type=str)
uri_parser = subparsers.add_parser("cfg_from_uri")
uri_parser.add_argument(
    "--uri", required=True, help="Enter the uri in the following format: `dbms://user:password@host:port/db/table`"
)


def parse_args():
    parsed_args = parser.parse_args(sys.argv[1:])

    if hasattr(parsed_args, "uri"):
        dsn, _, table = parsed_args.uri.rpartition("/")
        return {"uri": dsn, "table": table}

    elif hasattr(parsed_args, "file"):  # parse yaml input
        conf = OmegaConf.load(parsed_args.file)
        conf.merge_with_cli()

    else:
        sys.argv = [__file__] + [f"{key}={value}" for key, value in parsed_args.__dict__.items()]
        conf = OmegaConf.from_cli()

    return {
        "uri": "{type}://{user}:{password}@{host}:{port}/{name}".format(**conf._content["db"]),
        "table": conf._content["db"]["table"],
    }


script = {
    "root": {
        "start": {
            RESPONSE: "Hi",
            TRANSITIONS: {
                ("small_talk", "ask_some_questions"): cnd.exact_match("hi"),
                ("animals", "have_pets"): cnd.exact_match("i like animals"),
                ("animals", "like_animals"): cnd.exact_match("let's talk about animals"),
                ("news", "what_news"): cnd.exact_match("let's talk about news"),
            },
        },
        "fallback": {RESPONSE: "Oops"},
    },
    "animals": {
        "have_pets": {RESPONSE: "do you have pets?", TRANSITIONS: {"what_animal": cnd.exact_match("yes")}},
        "like_animals": {RESPONSE: "do you like it?", TRANSITIONS: {"what_animal": cnd.exact_match("yes")}},
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
                "ask_about_training": cnd.exact_match("i do not known"),
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
                "ask_about_science": cnd.exact_match("science"),
                "ask_about_sport": cnd.exact_match("sport"),
            },
        },
        "ask_about_science": {
            RESPONSE: "i got news about science, do you want to hear?",
            TRANSITIONS: {
                "science_news": cnd.exact_match("yes"),
                ("small_talk", "ask_some_questions"): cnd.exact_match("let's change the topic"),
            },
        },
        "science_news": {
            RESPONSE: "This is science news",
            TRANSITIONS: {
                "what_news": cnd.exact_match("ok"),
                ("small_talk", "ask_some_questions"): cnd.exact_match("let's change the topic"),
            },
        },
        "ask_about_sport": {
            RESPONSE: "i got news about sport, do you want to hear?",
            TRANSITIONS: {
                "sport_news": cnd.exact_match("yes"),
                ("small_talk", "ask_some_questions"): cnd.exact_match("let's change the topic"),
            },
        },
        "sport_news": {
            RESPONSE: "This is sport news",
            TRANSITIONS: {
                "what_news": cnd.exact_match("ok"),
                ("small_talk", "ask_some_questions"): cnd.exact_match("let's change the topic"),
            },
        },
    },
    "small_talk": {
        "ask_some_questions": {
            RESPONSE: "how are you",
            TRANSITIONS: {
                "ask_talk_about": cnd.exact_match("fine"),
                ("animals", "like_animals"): cnd.exact_match("let's talk about animals"),
                ("news", "what_news"): cnd.exact_match("let's talk about news"),
            },
        },
        "ask_talk_about": {
            RESPONSE: "what would you like to talk about?",
            TRANSITIONS: {
                ("animals", "like_animals"): cnd.exact_match("dog"),
                ("news", "what_news"): cnd.exact_match("let's talk about news"),
            },
        },
    },
}
