# %%
import random

from chatsky.script import Context, Message


def shuffle_dict_keys(dictionary: dict) -> dict:
    return {key: dictionary[key] for key in sorted(dictionary, key=lambda k: random.random())}


def test_context():
    ctx = Context()
    for index in range(0, 30, 2):
        ctx.add_request(Message(str(index)))
        ctx.add_label((str(index), str(index + 1)))
        ctx.add_response(Message(str(index + 1)))
    ctx.labels = shuffle_dict_keys(ctx.labels)
    ctx.requests = shuffle_dict_keys(ctx.requests)
    ctx.responses = shuffle_dict_keys(ctx.responses)
    ctx = Context.cast(ctx.model_dump_json())
    ctx.misc[123] = 312
    ctx.clear(5, ["requests", "responses", "misc", "labels", "framework_data"])
    ctx.misc["1001"] = "11111"
    ctx.add_request(Message(str(1000)))
    ctx.add_label((str(1000), str(1000 + 1)))
    ctx.add_response(Message(str(1000 + 1)))

    assert ctx.labels == {
        10: ("20", "21"),
        11: ("22", "23"),
        12: ("24", "25"),
        13: ("26", "27"),
        14: ("28", "29"),
        15: ("1000", "1001"),
    }
    assert ctx.requests == {
        10: Message("20"),
        11: Message("22"),
        12: Message("24"),
        13: Message("26"),
        14: Message("28"),
        15: Message("1000"),
    }
    assert ctx.responses == {
        10: Message("21"),
        11: Message("23"),
        12: Message("25"),
        13: Message("27"),
        14: Message("29"),
        15: Message("1001"),
    }
    assert ctx.misc == {"1001": "11111"}
    assert ctx.current_node is None
    ctx.model_dump_json()

    try:
        Context.cast(123)
    except ValueError:
        pass
