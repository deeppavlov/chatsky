# %%
import random

from dff.script import Context, Node, Message


def shuffle_dict_keys(dictionary: dict) -> dict:
    return {key: dictionary[key] for key in sorted(dictionary, key=lambda k: random.random())}


def test_context():
    ctx = Context()
    for index in range(0, 30, 2):
        ctx.add_request(Message(text=str(index)))
        ctx.add_label((str(index), str(index + 1)))
        ctx.add_response(Message(text=str(index + 1)))
    ctx.labels = shuffle_dict_keys(ctx.labels)
    ctx.requests = shuffle_dict_keys(ctx.requests)
    ctx.responses = shuffle_dict_keys(ctx.responses)
    ctx = Context.cast(ctx.model_dump_json())
    ctx.misc[123] = 312
    ctx.clear(5, ["requests", "responses", "misc", "labels", "framework_states"])
    ctx.misc["1001"] = "11111"
    ctx.add_request(Message(text=str(1000)))
    ctx.add_label((str(1000), str(1000 + 1)))
    ctx.add_response(Message(text=str(1000 + 1)))

    assert ctx.labels == {
        10: ("20", "21"),
        11: ("22", "23"),
        12: ("24", "25"),
        13: ("26", "27"),
        14: ("28", "29"),
        15: ("1000", "1001"),
    }
    assert ctx.requests == {
        10: Message(text="20"),
        11: Message(text="22"),
        12: Message(text="24"),
        13: Message(text="26"),
        14: Message(text="28"),
        15: Message(text="1000"),
    }
    assert ctx.responses == {
        10: Message(text="21"),
        11: Message(text="23"),
        12: Message(text="25"),
        13: Message(text="27"),
        14: Message(text="29"),
        15: Message(text="1001"),
    }
    assert ctx.misc == {"1001": "11111"}
    assert ctx.current_node is None
    ctx.overwrite_current_node_in_processing(Node(**{"response": Message(text="text")}))
    ctx.model_dump_json()

    try:
        Context.cast(123)
    except ValueError:
        pass
