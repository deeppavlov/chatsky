import logging

from dff.core.keywords import TRANSITIONS, GRAPH, RESPONSE, MISC
from dff.core import Context, Actor

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

# custom functions
def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


def inline_function(keyword):
    def cond(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return keyword in ctx.current_human_annotated_utterance[0]

    return cond


def repeater(ctx: Context, actor: Actor, *args, **kwargs) -> str:
    return f"Repeat: {ctx.current_human_annotated_utterance[0]}"


# a dialog script
flows = {
    "flow_start": {
        GRAPH: {
            "node_start": {
                RESPONSE: "hi",
                TRANSITIONS: {
                    ("flow_repeat", "node_repeat"): inline_function("repeat"),
                    ("flow_start", "node_start"): always_true,
                },
            }
        },
    },
    "flow_repeat": {
        GRAPH: {
            "node_repeat": {
                RESPONSE: "hi",
                TRANSITIONS: {("flow_repeat", "node_repeat"): always_true},
                MISC: {"speech_functions": ["Open.Attend"]},
            }
        },
    },
}


ctx = Context()
actor = Actor(flows, start_node_label=("flow_start", "node_start"))
while True:
    in_text = input("you: ")
    ctx.add_human_utterance(in_text)
    ctx = actor(ctx)
    print(f"bot: {ctx.actor_text_response}")
