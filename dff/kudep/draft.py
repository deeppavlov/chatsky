from dff.key_words import (
    triggers as TRIGGERS,
    entry_points as TRANSITIONS,
    global_entry_points as GLOBAL_TRANSITIONS,
    graph as GRAPH,
    response as RESPONSE,
    state_processing as PROCESSING,
)
from dff.utils import forward, back, repeat, previous  # , to_root
from dff.core import compile_actor
import dff.priorities as priorities

from extentions import intents
from extentions import speech_functions
from extentions import providers
from extentions import handlers
from extentions import generic_responses

import custom
from custom.annotators.entities import has_entities

kwargs1 = {}
kwargs2 = {}

script = {
    # Example of global transitions
    "globals": {
        GLOBAL_TRANSITIONS: {
            ("helper", "commit_suicide", priorities.high): r"i want to commit suicide",
            ("not_understand", priorities.high): r"i did not understan",
            ("generic_responses_for_extrav", "root", priorities.middle): generic_responses.intent,
        },
        GRAPH: {
            "not_understand": {
                RESPONSE: "Sorry for not being clear",
                TRANSITIONS: {previous: intents.always_true},
            }
        },
    },
    "hobbies": {
        TRIGGERS: [any, [r"hobbies", intents.yes_intent, speech_functions.open]],  # an optional param
        TRANSITIONS: {
            "have_you_hobby": r"hobbies",
            "reaction_on_hobby": [all, [r"hobbies", intents.yes_intent, speech_functions.open]],
            "custom_answer": custom.request,
        },
        GRAPH: {
            "have_you_hobby": {
                RESPONSE: ["Do you have any hobbies?", "Do you have favorite hobbies?"],  # choices by random
                TRANSITIONS: {
                    "reaction_on_hobby": [
                        any,
                        [r"hobbies", custom.COMPILED_PATTERN.pattern, has_entities("wiki:Q24423")],
                    ],
                    forward: intents.always_true,  # to_next gets "have_you_slot" as target state
                },
            },
            "have_you_slot": {
                RESPONSE: ["Do you have {SLOT1}?", "Do you have {SLOT2}?"],
                # TODO: What is the best way to put user parameters into state? For example SLOT1 and SLOT2
                PROCESSING: custom.state_processing,  # processing fills SLOT* , can be list of funcs or func
                TRANSITIONS: {back: intents.yes_intent},
            },
            "reaction_on_hobby": {
                RESPONSE: "I like {SLOT1} and {SLOT2}",
                PROCESSING: custom.entities_to_slots_processing(SLOT1="wiki:Q24423", SLOT2="cobot_entities:Location"),
                TRANSITIONS: {forward: intents.always_true},
            },
            "custom_answer": {
                RESPONSE: custom.response,
                TRANSITIONS: [
                    {
                        ("friends", "have_you_friends"): r"friends",
                        ("facts", "facts"): r"facts",
                        repeat: intents.always_true,  # repeat gets "have_you_slot" as target state
                    }
                ],
            },
        },
    },
    "generic_responses_for_extrav": generic_responses.create_new_flow(
        escape_conditions={
            ("have_you_hobby", "reaction_on_hobby", priorities.high): [
                all,
                [r"hobbies", intents.yes_intent, speech_functions.open],
            ],
            ("have_you_hobby", "reaction_on_hobby", priorities.low): [intents.always_true],
        },
        **kwargs1,
    ),
    "generic_responses_default": generic_responses.create_new_flow(priority=0.9, **kwargs2),
    "helper": {
        GRAPH: {
            "commit_suicide": {RESPONSE: "It's better to call 9 1 1 now."},  # go to root after
        },
    },
    "facts": {
        TRANSITIONS: {"facts": intents.facts},
        GRAPH: {"facts": {RESPONSE: providers.fact_provider("weather"), TRANSITIONS: {"facts": intents.facts}}},
    },
}


actor = compile_actor(script)
actor.add_post_handler(handlers.collect_stat)

# get state
# ....
# actor.run(state)
# responce ....
# ....
