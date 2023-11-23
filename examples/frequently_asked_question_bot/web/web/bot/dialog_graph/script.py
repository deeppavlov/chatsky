"""
Script
--------
This module defines a script that the bot follows during conversation.
"""
from dff.script import RESPONSE, TRANSITIONS, GLOBAL, Message
import dff.script.conditions as cnd

from .responses import answer_similar_question, FIRST_MESSAGE, FALLBACK_NODE_MESSAGE


pipeline_kwargs = {
    "script": {
        GLOBAL: {
            TRANSITIONS: {
                # an empty message is used to init a dialogue
                ("qa_flow", "welcome_node"): cnd.exact_match(Message(), skip_none=False),
                ("qa_flow", "answer_question"): cnd.true(),
            },
        },
        "qa_flow": {
            "welcome_node": {
                RESPONSE: FIRST_MESSAGE,
            },
            "answer_question": {
                RESPONSE: answer_similar_question,
            },
        },
        "service_flow": {
            "start_node": {},  # this is the start node, it simply redirects to welcome node
            "fallback_node": {  # this node will only be used if something goes wrong (e.g. an exception is raised)
                RESPONSE: FALLBACK_NODE_MESSAGE,
            },
        },
    },
    "start_label": ("service_flow", "start_node"),
    "fallback_label": ("service_flow", "fallback_node"),
}
