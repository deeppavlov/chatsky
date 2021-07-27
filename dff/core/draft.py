# %%
from keywords import GLOBAL_TO_STATES, TO_STATES, GRAPH, RESPONSE, PROCESSING
from flows import Flows, normalize_node_label


kwargs1 = {}
kwargs2 = {}

PRIORITIES_HIGH = 2.0
PRIORITIES_MIDDLE = 1.0
PRIORITIES_LOW = 0.5
#
def template_func_dict(*args, **kwargs):
    return {}


def template_func_tuple(*args, **kwargs):
    return ["123"]


def template_func_func(*args, **kwargs):
    return lambda x: x


INTENTS_ALWAYS_TRUE = template_func_dict
INTENTS_YES_INTENT = template_func_dict
INTENTS_FACTS = template_func_dict

GENERIC_RESPONSES_INTENT = template_func_dict
GENERIC_RESPONSES_CREATE_NEW_FLOW = template_func_dict

PROVIDERS_FACT_PROVIDER = template_func_tuple


CUSTOM_REQUEST = template_func_dict
CUSTOM_STATE_PROCESSING = template_func_dict
CUSTOM_ENTITIES_TO_SLOTS_PROCESSING = template_func_func
CUSTOM_RESPONSE = template_func_dict
CUSTOM_COMPILED_PATTERN = template_func_dict
CUSTOM_HAS_ENTITIES = template_func_dict
CUSTOM_SF_OPEN = template_func_dict
forward = back = repeat = previous = template_func_dict

flows = {
    # Example of global transitions
    "globals": {
        GLOBAL_TO_STATES: {
            ("helper", "commit_suicide", PRIORITIES_HIGH): r"i want to commit suicide",
            ("not_understand", PRIORITIES_HIGH): r"i did not understan",
            ("generic_responses_for_extrav", "root", PRIORITIES_MIDDLE): GENERIC_RESPONSES_INTENT,
        },
        GRAPH: {
            "not_understand": {
                RESPONSE: "Sorry for not being clear",
                TO_STATES: {previous: INTENTS_ALWAYS_TRUE},
            }
        },
    },
    "hobbies": {
        # TRIGGERS: [any, [r"hobbies", INTENTS_YES_INTENT, CUSTOM_SF_OPEN]],  # an optional param
        TO_STATES: {
            "have_you_hobby": r"hobbies",
            # "reaction_on_hobby": [all, [r"hobbies", INTENTS_YES_INTENT, CUSTOM_SF_OPEN]],
            "custom_answer": CUSTOM_REQUEST,
        },
        GRAPH: {
            "have_you_hobby": {
                RESPONSE: ["Do you have any hobbies?", "Do you have favorite hobbies?"],  # choices by random
                TO_STATES: {
                    # "reaction_on_hobby": [
                    #     any,
                    #     [r"hobbies", CUSTOM_COMPILED_PATTERN, CUSTOM_HAS_ENTITIES("wiki:Q24423")],
                    # ],
                    forward: INTENTS_ALWAYS_TRUE,  # to_next gets "have_you_slot" as target state
                },
            },
            "have_you_slot": {
                RESPONSE: ["Do you have {SLOT1}?", "Do you have {SLOT2}?"],
                # TODO: What is the best way to put user parameters into state? For example SLOT1 and SLOT2
                PROCESSING: CUSTOM_STATE_PROCESSING,  # processing fills SLOT* , can be list of funcs or func
                TO_STATES: {back: INTENTS_YES_INTENT},
            },
            "reaction_on_hobby": {
                RESPONSE: "I like {SLOT1} and {SLOT2}",
                PROCESSING: CUSTOM_ENTITIES_TO_SLOTS_PROCESSING(SLOT1="wiki:Q24423", SLOT2="cobot_entities:Location"),
                TO_STATES: {forward: INTENTS_ALWAYS_TRUE},
            },
            "custom_answer": {
                RESPONSE: CUSTOM_RESPONSE,
                TO_STATES: {
                    ("friends", "have_you_friends"): r"friends",
                    ("facts", "facts"): r"facts",
                    repeat: INTENTS_ALWAYS_TRUE,  # repeat gets "have_you_slot" as target state
                },
            },
        },
    },
    "generic_responses_for_extrav": GENERIC_RESPONSES_CREATE_NEW_FLOW(
        escape_conditions={
            ("have_you_hobby", "reaction_on_hobby", PRIORITIES_HIGH): [
                all,
                [r"hobbies", INTENTS_YES_INTENT, CUSTOM_SF_OPEN],
            ],
            ("have_you_hobby", "reaction_on_hobby", PRIORITIES_LOW): [INTENTS_ALWAYS_TRUE],
        },
        **kwargs1,
    ),
    "generic_responses_default": GENERIC_RESPONSES_CREATE_NEW_FLOW(priority=0.9, **kwargs2),
    "helper": {
        GRAPH: {
            "commit_suicide": {RESPONSE: "It's better to call 9 1 1 now."},  # go to root after
        },
    },
    "facts": {
        TO_STATES: {"facts": INTENTS_FACTS},
        GRAPH: {"facts": {RESPONSE: PROVIDERS_FACT_PROVIDER("weather"), TO_STATES: {"facts": INTENTS_FACTS}}},
    },
}


# get state
# ....
# actor.run(state)
# responce ....
# ....
# Flows.parse_obj({"flows": script})
flows1 = Flows(flows=flows)
flows1.dict()
import pprint

pprint.pprint(flows1.get_transitions(1, global_transition_flag=False))
# %%
from typing import Union, Any, Optional
from pydantic import BaseModel, validate_arguments, conlist
from flows import Flows, NodeLabelType
from context import Context


class Actor:
    @validate_arguments
    def __init__(self, flows: Union[Flows, dict], start_node_label=NodeLabelType, default_priority=1.0):
        self.flows = flows if isinstance(flows, Flows) else Flows(flows=flows)
        self.flows.run_flows_verification()
        self.start_node_label = normalize_node_label(start_node_label, flow_label="", default_priority=default_priority)
        self.default_priority = default_priority

    @validate_arguments
    def turn(
        self,
        context: Union[Context, dict, str] = {},
        return_dict=False,
        return_json=False,
    ) -> Union[Context, dict, str]:
        if not context:
            context = Context()
            context.add_human_utterance("")
        elif isinstance(context, dict):
            context = Context.parse_raw(context)
        elif isinstance(context, str):
            context = Context.parse_raw(context)
        elif not issubclass(type(context), Context):
            raise ValueError(
                f"context expexted as sub class of Context class or object of dict/str(json) type, but got {context}"
            )

        self.flows.get_transitions(self.default_priority, global_transition_flag=False)


Actor(flows)
