# %%
import random

from df_engine.core import Context


def shuffle_dict_keys(dictionary: dict) -> dict:
    return {key: dictionary[key] for key in sorted(dictionary, key=lambda k: random.random())}


def test_context():
    ctx = Context()
    for index in range(0, 30, 2):
        ctx.add_request(str(index))
        ctx.add_label([str(index), str(index + 1)])
        ctx.add_response(str(index + 1))
    ctx.labels = shuffle_dict_keys(ctx.labels)
    ctx.requests = shuffle_dict_keys(ctx.requests)
    ctx.responses = shuffle_dict_keys(ctx.responses)
    ctx = Context.cast(ctx.json())
    ctx.misc[123] = 312
    ctx.clear(5, ["requests", "responses", "misc", "labels", "framework_states"])
    ctx.misc[1001] = "11111"
    ctx.add_request(str(1000))
    ctx.add_label([str(1000), str(1000 + 1)])
    ctx.add_response(str(1000 + 1))

    assert ctx.labels == {
        10: ("20", "21"),
        11: ("22", "23"),
        12: ("24", "25"),
        13: ("26", "27"),
        14: ("28", "29"),
        15: ("1000", "1001"),
    }
    assert ctx.requests == {10: "20", 11: "22", 12: "24", 13: "26", 14: "28", 15: "1000"}
    assert ctx.responses == {10: "21", 11: "23", 12: "25", 13: "27", 14: "29", 15: "1001"}
    assert ctx.misc == {1001: "11111"}
    ctx.json()

    try:
        Context.cast(123)
    except ValueError:
        pass
