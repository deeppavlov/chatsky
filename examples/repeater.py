from dff import TRANSITIONS, GRAPH, RESPONSE
from dff import Context, Flows, Actor

# custom functions
def always_true(ctx: Context, flows: Flows, *args, **kwargs) -> bool:
    return True


def repeater(ctx: Context, flows: Flows, *args, **kwargs) -> str:
    return f"Repeat:   {ctx.current_human_annotated_utterance[0]}"


# a dialog script
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
while True:
    in_text = input("you: ")
    ctx.add_human_utterance(in_text)
    ctx = actor.turn(ctx)
    print(f"bot: {ctx.actor_text_response}")
