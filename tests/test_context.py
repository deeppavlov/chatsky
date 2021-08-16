# %%

from dff.core import Context


def test_context():
    ctx = Context()
    for index in range(0, 30, 2):
        ctx.add_request(str(index))
        ctx.add_node_label([str(index), str(index + 1)])
        ctx.add_response(str(index + 1))
    ctx.misc[123] = 312
    ctx.clear(5, ["requests", "responses", "mics", "node_labels"])
    ctx.misc[1001] = "11111"
    ctx.add_request(str(1000))
    ctx.add_node_label([str(1000), str(1000 + 1)])
    ctx.add_response(str(1000 + 1))

    assert ctx.node_labels == {
        10: ("20", "21"),
        11: ("22", "23"),
        12: ("24", "25"),
        13: ("26", "27"),
        14: ("28", "29"),
        15: ("1000", "1001"),
    }
    assert ctx.requests == {10: "20", 11: "22", 12: "24", 13: "26", 14: "28", 15: "1000"}
    assert ctx.responses == {10: "21", 11: "23", 12: "25", 13: "27", 14: "29", 15: "1001"}
    assert ctx.previous_index == 15
    assert ctx.current_index == 15
    assert ctx.misc == {1001: "11111"}
    ctx.json()
    # print(f"{test_context.__name__} passed")
