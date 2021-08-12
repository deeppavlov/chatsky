# %%

from dff.core.context import Context


def test_context():
    ctx = Context()
    for index in range(0, 30, 2):
        ctx.add_human_utterance(str(index), [index])
        ctx.add_node_label([str(index), str(index + 1)])
        ctx.add_actor_utterance(str(index + 1))
        ctx.add_actor_annotation([index + 1])
    ctx.shared_memory[123] = 312
    ctx.clear(5, ["human", "actor", "share", "labels"])
    ctx.shared_memory[1001] = "11111"
    ctx.add_human_utterance(str(1000), [1000])
    ctx.add_node_label([str(1000), str(1000 + 1)])
    ctx.add_actor_utterance(str(1000 + 1))
    ctx.add_actor_annotation([1000 + 1])
    assert ctx.current_human_annotated_utterance == ("1000", [1000])
    assert ctx.previous_human_annotated_utterance == ("1000", [1000])
    assert ctx.previous_actor_annotated_utterance == ("1001", [1001])
    assert ctx.node_label_history == {
        10: ("20", "21"),
        11: ("22", "23"),
        12: ("24", "25"),
        13: ("26", "27"),
        14: ("28", "29"),
        15: ("1000", "1001"),
    }
    assert ctx.human_utterances == {10: "20", 11: "22", 12: "24", 13: "26", 14: "28", 15: "1000"}
    assert ctx.human_annotations == {10: [20], 11: [22], 12: [24], 13: [26], 14: [28], 15: [1000]}
    assert ctx.actor_utterances == {10: "21", 11: "23", 12: "25", 13: "27", 14: "29", 15: "1001"}
    assert ctx.actor_annotations == {10: [21], 11: [23], 12: [25], 13: [27], 14: [29], 15: [1001]}
    assert ctx.previous_history_index == 15
    assert ctx.current_history_index == 15
    assert ctx.shared_memory == {1001: "11111"}
    ctx.json()
    print(f"{test_context.__name__} passed")


test_context()
