from dff.core.keywords import GLOBAL, GRAPH, RESPONSE, GLOBAL_TRANSITIONS, TRANSITIONS
from dff.core import Context, Actor
from dff.transitions import repeat, previous, to_start, to_fallback, forward, backward


def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


def create_transitions():
    return {
        ("left", "step_2"): "left",
        ("right", "step_2"): "right",
        previous(): "previous",
        to_start(): "start",
        to_fallback(): "fallback",
        forward(): "forward",
        backward(): "back",
        previous(): "previous",
        repeat(): always_true,
    }


# a dialog script
plot = {
    GLOBAL: {TRANSITIONS: {**create_transitions()}},
    "root": {
        "start": {RESPONSE: "s"},
        "fallback": {RESPONSE: "f"},
    },
    "left": {
        "step_0": {RESPONSE: "l0"},
        "step_1": {RESPONSE: "l1"},
        "step_2": {RESPONSE: "l2"},
        "step_3": {RESPONSE: "l3"},
        "step_4": {RESPONSE: "l4"},
    },
    "right": {
        "step_0": {RESPONSE: "r0"},
        "step_1": {RESPONSE: "r1"},
        "step_2": {RESPONSE: "r2"},
        "step_3": {RESPONSE: "r3"},
        "step_4": {RESPONSE: "r4"},
    },
}


def test_transitions():
    ctx = Context()
    actor = Actor(plot, start_node_label=("root", "start"), fallback_node_label=("root", "fallback"))
    for in_text, out_text in [
        ("start", "s"),
        ("left", "l2"),
        # ("left", "l2"),
        # ("123", "l2"),
        # ("asd", "l2"),
        # ("right", "r2"),
        # ("fallback", "f"),
        # ("left", "l2"),
        # ("forward", "l3"),
        # ("forward", "l4"),
        # ("forward", "f"),
        # ("right", "r2"),
        # ("back", "r1"),
        # ("back", "r0"),
        # ("back", "f"),
        # ("start", "s"),
    ]:
        ctx.add_request(in_text)
        ctx = actor(ctx)
        if ctx.last_response != out_text:
            raise Exception(f" expected {out_text=} but got {ctx.last_response=} for {in_text=}")
