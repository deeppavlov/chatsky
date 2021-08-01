# %%
from keywords import GLOBAL_TRANSITIONS, TRANSITIONS, GRAPH, RESPONSE, PROCESSING
from flows import Flows, normalize_node_label


kwargs1 = {}
kwargs2 = {}

PRIORITIES_HIGH = 2.0
PRIORITIES_MIDDLE = 1.0
PRIORITIES_LOW = 0.5
#
def template_func_dict(*args, **kwargs):
    return {}


def template_func_label(*args, **kwargs):
    return ("hobbies", "have_you_hobby", PRIORITIES_HIGH)


def template_func_str(*args, **kwargs):
    return "asdasda"


def template_func_tuple(*args, **kwargs):
    return ["123"]


def template_func_func(*args, **kwargs):
    return lambda x: x


def always_true(*args, **kwargs):
    return True


def to_have_you_slot(*args, **kwargs):
    return ("hobbies", "have_you_slot", PRIORITIES_MIDDLE)


def processing_func(*args, **kwargs):
    return args[0], args[1]


INTENTS_ALWAYS_TRUE = always_true
INTENTS_YES_INTENT = template_func_dict
INTENTS_FACTS = template_func_dict

GENERIC_RESPONSES_INTENT = template_func_dict
GENERIC_RESPONSES_CREATE_NEW_FLOW = template_func_dict

PROVIDERS_FACT_PROVIDER = template_func_tuple


CUSTOM_REQUEST = template_func_dict
CUSTOM_STATE_PROCESSING = processing_func
CUSTOM_ENTITIES_TO_SLOTS_PROCESSING = template_func_func
CUSTOM_RESPONSE = template_func_str
CUSTOM_COMPILED_PATTERN = template_func_dict
CUSTOM_HAS_ENTITIES = template_func_dict
CUSTOM_SF_OPEN = template_func_dict
forward = back = repeat = previous = template_func_label
forward = to_have_you_slot

flows = {
    # Example of global transitions
    "globals": {
        GLOBAL_TRANSITIONS: {
            ("helper", "commit_suicide", PRIORITIES_HIGH): r"i want to commit suicide",
            ("not_understand", PRIORITIES_HIGH): r"i did not understan",
            ("helper", "commit_suicide", PRIORITIES_MIDDLE): GENERIC_RESPONSES_INTENT,
            ("hobbies", "have_you_hobby", PRIORITIES_MIDDLE): always_true,
        },
        GRAPH: {
            "not_understand": {
                RESPONSE: "Sorry for not being clear",
                TRANSITIONS: {previous: INTENTS_ALWAYS_TRUE},
            }
        },
    },
    "hobbies": {
        # TRIGGERS: [any, [r"hobbies", INTENTS_YES_INTENT, CUSTOM_SF_OPEN]],  # an optional param
        GLOBAL_TRANSITIONS: {
            "have_you_hobby": r"hobbies",
            # "reaction_on_hobby": [all, [r"hobbies", INTENTS_YES_INTENT, CUSTOM_SF_OPEN]],
            "custom_answer": CUSTOM_REQUEST,
        },
        GRAPH: {
            "have_you_hobby": {
                RESPONSE: ["Do you have any hobbies?", "Do you have favorite hobbies?"],  # choices by random
                TRANSITIONS: {
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
                TRANSITIONS: {back: INTENTS_YES_INTENT},
            },
            "reaction_on_hobby": {
                RESPONSE: "I like {SLOT1} and {SLOT2}",
                PROCESSING: CUSTOM_ENTITIES_TO_SLOTS_PROCESSING(SLOT1="wiki:Q24423", SLOT2="cobot_entities:Location"),
                TRANSITIONS: {forward: INTENTS_ALWAYS_TRUE},
            },
            "custom_answer": {
                RESPONSE: CUSTOM_RESPONSE,
                TRANSITIONS: {
                    ("hobbies", "have_you_hobby"): r"friends",
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
        GLOBAL_TRANSITIONS: {"facts": INTENTS_FACTS},
        GRAPH: {"facts": {RESPONSE: PROVIDERS_FACT_PROVIDER("weather"), TRANSITIONS: {"facts": INTENTS_FACTS}}},
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
# import pprint

# pprint.pprint(flows1.get_transitions(1, global_transition_flag=False))
import heapq

from typing import Union, Any, Optional, Callable
from pydantic import BaseModel, validate_arguments, conlist
from flows import Flows, NodeLabelType, Node
from context import Context


def deep_copy_condition_handler(condition: Callable, ctx: Context, flows: Flows, *args, **kwargs):
    return condition(ctx.copy(deep=True), flows.copy(deep=True), *args, **kwargs)


class Actor:
    @validate_arguments
    def __init__(
        self,
        flows: Union[Flows, dict],
        start_node_label: tuple[str, str],
        fallback_node_label: Optional[tuple[str, str]] = None,
        default_priority: float = 1.0,
        response_validation_flag: Optional[bool] = None,
        validation_logging_flag: bool = True,
        *args,
        **kwargs,
    ):
        self.flows = flows if isinstance(flows, Flows) else Flows(flows=flows)
        errors = self.flows.validate_flows(response_validation_flag, validation_logging_flag)
        if errors:
            raise ValueError(
                f"Found {len(errors)} errors: " + " ".join([f"{i}) {er}" for i, er in enumerate(errors, 1)])
            )
        self.start_node_label = normalize_node_label(start_node_label, flow_label="", default_priority=default_priority)
        if self.flows.get_node(self.start_node_label) is None:
            raise ValueError(f"Unkown start_node_label = {self.start_node_label}")
        if fallback_node_label is None:
            self.fallback_node_label = self.start_node_label
        else:
            self.fallback_node_label = normalize_node_label(
                fallback_node_label,
                flow_label="",
                default_priority=default_priority,
            )
            if self.flows.get_node(self.fallback_node_label) is None:
                raise ValueError(f"Unkown fallback_node_label = {self.fallback_node_label}")

        self.default_priority = default_priority

    @validate_arguments
    def turn(
        self,
        ctx: Union[Context, dict, str] = {},
        return_dict=False,
        return_json=False,
        condition_handler: Callable = deep_copy_condition_handler,
        *args,
        **kwargs,
    ) -> Union[Context, dict, str]:
        if not ctx:
            ctx = Context()
            ctx.add_node_label(self.start_node_label[:2])
            ctx.add_human_utterance("")
        elif isinstance(ctx, dict):
            ctx = Context.parse_raw(ctx)
        elif isinstance(ctx, str):
            ctx = Context.parse_raw(ctx)
        elif not issubclass(type(ctx), Context):
            raise ValueError(
                f"context expexted as sub class of Context class or object of dict/str(json) type, but got {ctx}"
            )

        previous_node_label = (
            normalize_node_label(ctx.previous_node_label, "", self.default_priority)
            if ctx.previous_node_label
            else self.start_node_label
        )
        flow_label, node = self.get_node(previous_node_label)

        # TODO: deepcopy for node_label
        global_transitions = self.flows.get_transitions(self.default_priority, True)
        global_true_node_label = self.get_true_node_label(global_transitions, ctx, condition_handler, flow_label)

        local_transitions = node.get_transitions(flow_label, self.default_priority, False)
        local_true_node_label = self.get_true_node_label(local_transitions, ctx, condition_handler, flow_label)

        true_node_label = self.choose_true_node_label(local_true_node_label, global_true_node_label)

        ctx.add_node_label(true_node_label[:2])
        flow_label, next_node = self.get_node(true_node_label)
        processing = next_node.get_processing()
        _, tmp_node = processing(flow_label, next_node, ctx, self.flows, *args, **kwargs)

        response = tmp_node.get_response()
        text = response(ctx, self.flows, *args, **kwargs)
        ctx.add_actor_utterance(text)

        return ctx

    @validate_arguments
    def get_true_node_label(
        self,
        transitions: dict,
        ctx: Context,
        condition_handler: Callable,
        flow_label: str,
        *args,
        **kwargs,
    ) -> Optional[tuple[str, str, float]]:
        true_node_labels = []
        for node_label, condition in transitions.items():
            if condition_handler(condition, ctx, self.flows, *args, **kwargs):
                if isinstance(node_label, Callable):
                    node_label = node_label(ctx, self.flows, *args, **kwargs)
                    if node_label is None:
                        continue
                node_label = normalize_node_label(node_label, flow_label, self.default_priority)
                heapq.heappush(true_node_labels, (node_label[2], node_label))
        true_node_label = true_node_labels[0][1] if true_node_labels else None
        return true_node_label

    @validate_arguments
    def get_node(
        self,
        node_label: tuple[str, str, float],
    ) -> tuple[str, Node]:
        node = self.flows.get_node(node_label)
        if node is None:
            node, node_label = self.flows.get_node(self.start_node_label), self.start_node_label
        flow_label = node_label[0]
        return flow_label, node

    @validate_arguments
    def choose_true_node_label(
        self,
        local_true_node_label: Optional[tuple[str, str, float]],
        global_true_node_label: Optional[tuple[str, str, float]],
    ) -> tuple[str, str, float]:
        if all([local_true_node_label, global_true_node_label]):
            true_node_label = (
                local_true_node_label
                if local_true_node_label[2] >= global_true_node_label[2]
                else global_true_node_label
            )
        elif any([local_true_node_label, global_true_node_label]):
            true_node_label = local_true_node_label if local_true_node_label else global_true_node_label
        else:
            true_node_label = self.fallback_node_label
        return true_node_label


def repeater(ctx, flows, *args, **kwargs):
    return f"Repeat:   {ctx.current_human_annotated_utterance[0]}"


flows = {
    "start": {
        TRANSITIONS: {"start": always_true},
        GRAPH: {
            "start": {
                RESPONSE: "hi",
                TRANSITIONS: {("repeat", "repeat"): always_true},
            }
        },
    },
    "repeat": {
        GRAPH: {
            "repeat": {
                RESPONSE: repeater,
                TRANSITIONS: {("repeat", "repeat"): always_true},
            }
        },
    },
}
ctx = Context()
print(f"{ctx=}")
actor = Actor(flows, ("start", "start"))
for in_text in range(10):
    in_text = "in_text " + str(in_text)
    ctx.add_human_utterance(in_text)
    ctx = actor(ctx)
    print(f"{in_text=}")
    # print(f"out_text={ctx.}")
    print(f"{ctx.actor_utterances=}")
# %%
