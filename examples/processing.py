import logging
from typing import Optional
import datetime


from dff import GRAPH, RESPONSE, TRANSITIONS, PROCESSING
from dff import Context, Actor, Node
from dff import repeat, previous, to_start, to_fallback, forward, back

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)


# custom functions
def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


def create_transitions():
    return {
        ("left", "step_2"): "left",
        ("right", "step_2"): "right",
        previous(): "previous",
        to_start(): "start",
        forward(): "forward",
        back(): "back",
        previous(): "previous",
        repeat(): "repeat",
        to_fallback(): always_true,
    }


def add_node_label_processing(
    node_label: str,
    node: Node,
    ctx: Context,
    actor: Actor,
    *args,
    **kwargs,
) -> Optional[tuple[str, Node]]:
    node.response = [f"{node_label}: {resp}" for resp in node.response]
    return node_label, node


def add_time_processing(
    node_label: str,
    node: Node,
    ctx: Context,
    actor: Actor,
    *args,
    **kwargs,
) -> Optional[tuple[str, Node]]:
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    node.response = [f"{timestamp}: {resp}" for resp in node.response]
    return node_label, node


# a dialog script
flows = {
    "root": {
        GRAPH: {
            "start": {
                RESPONSE: "start",
                TRANSITIONS: {("greeting", "step_0"): always_true},
            },
            "fallback": {RESPONSE: "the end"},
        },
    },
    "greeting": {
        GRAPH: {
            "step_0": {
                PROCESSING: [add_node_label_processing, add_time_processing],
                RESPONSE: ["hi", "hello"],
                TRANSITIONS: {forward(): always_true},
            },
            "step_1": {
                PROCESSING: [add_node_label_processing, add_time_processing],
                RESPONSE: ["how are you", "what's up"],
                TRANSITIONS: {forward(): always_true},
            },
            "step_2": {
                PROCESSING: [add_node_label_processing, add_time_processing],
                RESPONSE: ["ok", "good"],
            },
        },
    },
}

ctx = Context()
actor = Actor(flows, start_node_label=("root", "start"), fallback_node_label=("root", "fallback"))
while True:
    in_text = input("you: ")
    ctx.add_human_utterance(in_text)
    ctx = actor(ctx)
    print(f"bot: {ctx.actor_text_response}")

# Outputs:
