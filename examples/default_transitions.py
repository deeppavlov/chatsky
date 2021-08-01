from typing import Optional
from dff import TRANSITIONS, GRAPH, RESPONSE, GLOBAL_TRANSITIONS
from dff import Context, Actor

# custom functions
def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


def inline_function(keyword):
    def cond(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return keyword in ctx.current_human_annotated_utterance[0]

    return cond


def repeat(priority: Optional[float] = None, *args, **kwargs):
    def repeat_transition(ctx: Context, actor: Actor, *args, **kwargs) -> tuple[str, str, float]:
        previous_index = ctx.previous_history_index()
        flow_label, node_label = ctx.node_label_history.get(previous_index, actor.fallback_node_label)
        current_priority = actor.default_priority if priority is None else priority
        return (flow_label, node_label, current_priority)


def pri(priority: Optional[float] = None, *args, **kwargs):
    def repeat_transition(ctx: Context, actor: Actor, *args, **kwargs) -> tuple[str, str, float]:
        previous_index = ctx.previous_history_index()
        flow_label, node_label = ctx.node_label_history[previous_index]
        current_priority = actor.default_priority if priority is None else priority
        return (flow_label, node_label, current_priority)


def repeat_response(ctx: Context, actor: Actor, *args, **kwargs) -> str:
    previous_index = ctx.previous_history_index()
    ctx.node_label_history[previous_index]
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
                RESPONSE: repeat_response,
                TRANSITIONS: {repeat(): always_true},
            }
        },
    },
}


ctx = Context()
print(f"{ctx=}")
actor = Actor(flows, start_node_label=("start", "start"))
print(f"{actor=}")
while True:
    in_text = input("you: ")
    ctx.add_human_utterance(in_text)
    ctx = actor(ctx)
    print(f"bot: {ctx.actor_text_response}")
