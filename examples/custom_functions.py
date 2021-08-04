import logging

from dff import TRANSITIONS, GRAPH, RESPONSE
from dff import Context, Actor

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
    "start": {
        GRAPH: {
            "start": {
                RESPONSE: "hi",
                TRANSITIONS: {
                    ("repeat", "repeat"): inline_function("repeat"),
                    ("start", "start"): always_true,
                },
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
actor = Actor(flows, start_node_label=("start", "start"))
while True:
    in_text = input("you: ")
    ctx.add_human_utterance(in_text)
    ctx = actor(ctx)
    print(f"bot: {ctx.actor_text_response}")
