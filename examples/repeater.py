from dff import TRANSITIONS, GRAPH, RESPONSE, GLOBAL_TRANSITIONS
from dff import Context, Flows, Actor

# custom functions
def always_true(ctx: Context, flows: Flows, *args, **kwargs) -> bool:
    return True


def inline_function(keyword):
    def cond(ctx: Context, flows: Flows, *args, **kwargs) -> bool:
        return keyword in ctx.current_human_annotated_utterance[0]

    return cond


def repeater(ctx: Context, flows: Flows, *args, **kwargs) -> str:
    return f"Repeat: {ctx.current_human_annotated_utterance[0]}"


# a dialog script
flows = {
    "start": {
        GLOBAL_TRANSITIONS: {"start": always_true},
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
print(f"{ctx=}")
actor = Actor(flows, start_node_label=("start", "start"))
while True:
    in_text = input("you: ")
    ctx.add_human_utterance(in_text)
    ctx = actor(ctx)
    print(f"bot: {ctx.actor_text_response}")
