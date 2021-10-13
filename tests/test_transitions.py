# from dff.core.keywords import GLOBAL, RESPONSE, TRANSITIONS
# from dff.core import Context, Actor
# from dff.transitions import repeat, previous, to_start, to_fallback, forward, backward
# from dff.conditions import exact_match, true


# def create_transitions():
#     return {
#         ("left", "step_2"): exact_match("left"),
#         ("right", "step_2"): exact_match("right"),
#         previous(): exact_match("previous"),
#         to_start(): exact_match("start"),
#         to_fallback(): exact_match("fallback"),
#         forward(): exact_match("forward"),
#         backward(): exact_match("back"),
#         previous(): exact_match("previous"),
#         repeat(): true(),
#     }


# # a dialog script
# plot = {
#     GLOBAL: {TRANSITIONS: {**create_transitions()}},
#     "root": {
#         "start": {RESPONSE: "s"},
#         "fallback": {RESPONSE: "f"},
#     },
#     "left": {
#         "step_0": {RESPONSE: "l0"},
#         "step_1": {RESPONSE: "l1"},
#         "step_2": {RESPONSE: "l2"},
#         "step_3": {RESPONSE: "l3"},
#         "step_4": {RESPONSE: "l4"},
#     },
#     "right": {
#         "step_0": {RESPONSE: "r0"},
#         "step_1": {RESPONSE: "r1"},
#         "step_2": {RESPONSE: "r2"},
#         "step_3": {RESPONSE: "r3"},
#         "step_4": {RESPONSE: "r4"},
#     },
# }


# # def test_transitions():
# #     ctx = Context()
# #     actor = Actor(plot, start_label=("root", "start"), fallback_label=("root", "fallback"))
# #     for in_text, out_text in [
# #         ("start", "s"),
# #         ("left", "l2"),
# #         ("left", "l2"),
# #         ("123", "l2"),
# #         ("asd", "l2"),
# #         ("right", "r2"),
# #         ("fallback", "f"),
# #         ("left", "l2"),
# #         ("forward", "l3"),
# #         ("forward", "l4"),
# #         ("forward", "f"),
# #         ("right", "r2"),
# #         ("back", "r1"),
# #         ("back", "r0"),
# #         ("back", "f"),
# #         ("start", "s"),
# #     ]:
# #         ctx.add_request(in_text)
# #         ctx = actor(ctx)
# #         if ctx.last_response != out_text:
# #             raise Exception(f" expected {out_text=} but got {ctx.last_response=} for {in_text=}")


# def test_transitions():
#     ctx = Context()
#     actor = Actor(plot, start_label=("root", "start"), fallback_label=("root", "fallback"))
#     for in_text, out_text in [
#         ("start", "s"),
#         ("left", "l2"),
#         ("left", "l2"),
#         ("123", "l2"),
#         ("asd", "l2"),
#         ("right", "r2"),
#         ("fallback", "f"),
#         ("left", "l2"),
#         ("forward", "l3"),
#         ("forward", "l4"),
#         ("forward", "f"),
#         ("right", "r2"),
#         ("back", "r1"),
#         ("back", "r0"),
#         ("back", "f"),
#         ("start", "s"),
#     ]:
#         ctx.add_request(in_text)
#         ctx = actor(ctx)
#         if ctx.last_response != out_text:
#             raise Exception(f" expected {out_text=} but got {ctx.last_response=} for {in_text=}")


# %%
from dff.core import Context, Actor
from dff.transitions import forward, repeat, previous, to_fallback, to_start, backward

def test_transitions():
    ctx = Context()
    ctx.add_label(["flow", "node1"])
    ctx.add_label(["flow", "node2"])
    ctx.add_label(["flow", "node3"])
    ctx.add_label(["flow", "node2"])
    actor = Actor(
        plot={"flow": {"node1": {}, "node2": {}, "node3": {}},"service": {"start": {}, "fallback": {}}},
        start_label=("service", "start"),
        fallback_label=("service", "fallback"),
    )

    assert repeat(99)(ctx, actor) == ("flow", "node2", 99)
    assert previous(99)(ctx, actor) == ("flow", "node3", 99)
    assert to_fallback(99)(ctx, actor) == ("service", "fallback", 99)
    assert to_start(99)(ctx, actor) == ("service", "start", 99)
    assert forward(99)(ctx, actor) == ("flow", "node3", 99)
    assert backward(99)(ctx, actor) == ("flow", "node1", 99)

    ctx.add_label(["flow", "node3"])
    assert forward(99)(ctx, actor) == ("flow", "node1", 99)
    assert forward(99,cyclicality_flag=False)(ctx, actor) == ("service", "fallback", 99)

    ctx.add_label(["flow", "node1"])
    assert backward(99)(ctx, actor) == ("flow", "node3", 99)
    assert backward(99,cyclicality_flag=False)(ctx, actor) == ("service", "fallback", 99)
