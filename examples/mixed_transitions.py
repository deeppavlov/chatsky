import logging

from dff.core.keywords import GRAPH, RESPONSE, GLOBAL_TRANSITIONS, TRANSITIONS
from dff.core import Context, Actor
from dff.transitions import to_start, to_fallback, forward, back

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)


# custom functions
def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


# a dialog script
flows = {
    "root": {
        GLOBAL_TRANSITIONS: {
            to_fallback(priority=0.1): always_true,
            back(priority=0.11): "back",
            forward(priority=0.2): "forward",
            to_start(priority=1.15): "start",
        },
        GRAPH: {
            "start": {
                RESPONSE: "start msg",
                TRANSITIONS: {
                    ("left", "step_1", 1.11): "left one",
                    ("left", "step_0", 1.0): "left",
                    ("left", "step_2", 1.1): "left two",
                    ("right", "step_1", 1.11): "right one",
                    ("right", "step_0"): "right",
                    ("right", "step_2", 1.1): "right two",
                },
            },
            "fallback": {RESPONSE: "fallback msg"},
        },
    },
    "left": {
        GRAPH: {
            "step_0": {RESPONSE: "0 left step msg"},
            "step_1": {RESPONSE: "1 left step msg"},
            "step_2": {RESPONSE: "2 left step msg"},
            "step_3": {RESPONSE: "3 left step msg"},
            "step_4": {RESPONSE: "4 left step msg"},
        },
    },
    "right": {
        GRAPH: {
            "step_0": {RESPONSE: "0 right step msg"},
            "step_1": {RESPONSE: "1 right step msg"},
            "step_2": {RESPONSE: "2 right step msg"},
            "step_3": {RESPONSE: "3 right step msg"},
            "step_4": {RESPONSE: "4 right step msg"},
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
# you: start
# bot: start msg
#
# you: left
# bot: 2 left step msg
#
# you: back
# bot: 1 left step msg
#
# you: back
# bot: 0 left step msg
#
# you: right
# bot: 2 right step msg
#
# you: forward
# bot: 3 right step msg
#
# you: left
# bot: 2 left step msg
#
# you: previous
# bot: 3 right step msg
#
# you: fallback
# bot: fallback msg
#
# you: left
# bot: 2 left step msg
#
# you: repeat
# bot: 2 left step msg
#
# you: qweqweqweqwe
# bot: fallback msg
