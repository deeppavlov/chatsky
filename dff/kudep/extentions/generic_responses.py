import copy

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


GENERIC_REACTION_TO_USER_SPEECH_FUNCTION = {
    "React.Rejoinder.Support.Track.Check": ["Pardon?", "I beg your pardon?", "Mhm ?", "Hm?", "What do you mean?"],
    "React.Rejoinder.Track.Check": ["Pardon?", "I beg your pardon?", "Mhm ?", "Hm?", "What do you mean?"],
    "React.Rejoinder.Support.Track.Confirm": [
        "Oh really?",
        "Oh yeah?",
        "Sure?",
        "Are you sure?",
        "Are you serious?",
        "Yeah",
    ],
    "React.Respond.Confront.Reply.Contradict": [
        "Oh definitely no",
        "No",
        "No way",
        "Absolutely not",
        "Not at all",
        "Nope",
        "Not really",
        "Hardly",
    ],
    "React.Respond.Reply.Contradict": [
        "Oh definitely no",
        "No",
        "No way",
        "Absolutely not",
        "Not at all",
        "Nope",
        "Not really",
        "Hardly",
    ],
    "React.Respond.Confront.Reply.Disawow": [
        "I doubt it. I really do.",
        "I don't know.",
        "I'm not sure",
        "Probably.",
        "I don't know if it's true",
    ],
    "React.Respond.Reply.Disawow": [
        "I doubt it. I really do.",
        "I don't know.",
        "I'm not sure",
        "Probably.",
        "I don't know if it's true",
    ],
    "React.Respond.Confront.Reply.Disagree": [
        "No",
        "Hunhunh.",
        "I don't agree with you",
        "I disagree",
        "I do not think so",
        "I hardly think so",
        "I can't agree with you",
    ],
    "React.Respond.Reply.Disagree": [
        "No",
        "Hunhunh.",
        "I don't agree with you",
        "I disagree",
        "I do not think so",
        "I hardly think so",
        "I can't agree with you",
    ],
    "React.Respond.Support.Reply.Affirm": [
        "Oh definitely.",
        "Yeah.",
        "Kind of.",
        "Unhunh",
        "Yeah I think so",
        "Really.",
        "Right.",
        "That's what it was.",
    ],
    "React.Respond.Support.Reply.Acknowledge": [
        "I knew that.",
        "I know.",
        "No doubts",
        "I know what you meant.",
        "Oh yeah.",
        "I see",
    ],
    "React.Respond.Reply.Acknowledge": [
        "I knew that.",
        "I know.",
        "No doubts",
        "I know what you meant.",
        "Oh yeah.",
        "I see",
    ],
    "React.Respond.Support.Reply.Agree": [
        "Oh that's right. That's right.",
        "Yep.",
        "Right.",
        "Sure",
        "Indeed",
        "I agree with you",
    ],
    "React.Respond.Reply.Agree": [
        "Oh that's right. That's right.",
        "Yep.",
        "Right.",
        "Sure",
        "Indeed",
        "I agree with you",
    ],
    "Sustain.Continue.Monitor": ["You know?", "Alright?", "Yeah?", "See?", "Right?"],
}
markup_template = (
    {
        TRANSITIONS: {"facts": intents.facts},
        GRAPH: {"facts": {RESPONSE: providers.fact_provider("weather"), TRANSITIONS: {"facts": intents.facts}}},
    },
)


def create_new_flow(**kwargs):
    new_flow = {TRANSITIONS: {}}
    for label, answer in GENERIC_REACTION_TO_USER_SPEECH_FUNCTION.items():
        # new_flow[TRANSITIONS][label] = any ....
        # ..
        pass
    # ...
    return new_flow
