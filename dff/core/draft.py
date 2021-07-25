# %%
from keywords import GLOBAL_TO_STATES, TO_STATES, GRAPH, RESPONSE, PROCESSING
from models_v2 import Flows


# from dff.utils import forward, back, repeat, previous  # , to_root
# from dff.core import compile_actor
# import dff.PRIORITIES_AS_PRIORITIES

# from extentions import intents
# from extentions import custom
# from extentions import providers
# from extentions import handlers
# from extentions import generic_responses

# import custom
# from custom.annotators.entities import has_entities

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

script = {
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
# %%

s1 = Script(flows=script)
s1.json()

class Context(BaseModel):
    history : list[str] = []


class Actor():
    def __init__(self, script: dict, start_state=Union[tuple, list, str, Callable, ToState]):
        self.script = Script(flows=script)
        self.start_state = start_state if isinstance(start_state, ToState) else ToState.parse(start_state)

    def turn(context: Union[Context, dict, str], return_dict=False, return_json=False) -> Union[Context, dict, str]:
        

# get state
# ....
# actor.run(state)
# responce ....
# ....
# %%
Flows.parse_obj({"flows":script})