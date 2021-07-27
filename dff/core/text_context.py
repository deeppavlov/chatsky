# %%

from context import Context


def test_context():
    context = Context()
    for index in range(0, 30, 2):
        context.add_human_utterance(str(index), [index])
        context.add_actor_utterance(str(index + 1), [index + 1])
        context.add_node_label([str(index), str(index + 1)])
    context.shared_memory[123] = 312
    context.clean_context(5, ["human", "actor", "share", "labels"])
    context.shared_memory[1001] = "11111"
    context.add_human_utterance(str(1000), [1000])
    context.add_actor_utterance(str(1000 + 1), [1000 + 1])
    context.add_node_label([str(1000), str(1000 + 1)])
    assert context.get_current_human_annotated_utterance() == ("1000", [1000])
    assert context.get_previous_human_annotated_utterance() == ("1000", [1000])
    assert context.get_previous_actor_annotated_utterance() == ("1001", [1001])
    assert context.node_label_history == {
        10: ("20", "21"),
        11: ("22", "23"),
        12: ("24", "25"),
        13: ("26", "27"),
        14: ("28", "29"),
        15: ("1000", "1001"),
    }
    assert context.human_utterances == {10: "20", 11: "22", 12: "24", 13: "26", 14: "28", 15: "1000"}
    assert context.human_annotations == {10: [20], 11: [22], 12: [24], 13: [26], 14: [28], 15: [1000]}
    assert context.actor_utterances == {10: "21", 11: "23", 12: "25", 13: "27", 14: "29", 15: "1001"}
    assert context.actor_annotations == {10: [21], 11: [23], 12: [25], 13: [27], 14: [29], 15: [1001]}
    assert context.previous_history_index == 15
    assert context.current_history_index == 15
    assert context.shared_memory == {1001: "11111"}


test_context()
