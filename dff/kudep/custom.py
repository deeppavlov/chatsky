from extentions import intents


import re

COMPILED_PATTERN = re.compile(r"pattern")


def state_processing(vars):
    pass


def unrepeat_processing(vars):
    pass


def request(vars):
    return True


def response(vars):
    vars["bot_name"] = "jack"
    bot_name = vars["bot_name"]
    return f"I like talk with you, btw my name is {bot_name}"


def to_states(vars):
    return {("hobbies", "have_you_hobby"): intents.always_true}
