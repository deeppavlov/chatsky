# %%
import itertools

from dff.script import (
    GLOBAL,
    TRANSITIONS,
    RESPONSE,
    MISC,
    PRE_RESPONSE_PROCESSING,
    PRE_TRANSITIONS_PROCESSING,
    Script,
    Node,
    Message,
)


def positive_test(samples, custom_class):
    results = []
    for sample in samples:
        try:
            res = custom_class(**sample)
            results += [res]
        except Exception as exception:
            raise Exception(f"sample={sample} gets exception={exception}")
    return results


def negative_test(samples, custom_class):
    for sample in samples:
        try:
            custom_class(**sample)
        except Exception:  # TODO: special type of exceptions
            continue
        raise Exception(f"sample={sample} can not be passed")


def std_func(ctx, actor, *args, **kwargs):
    pass


def test_node_creation():
    node_creation(PRE_RESPONSE_PROCESSING)


def node_creation(pre_response_proc):
    samples = {
        "transition": [std_func, "node", ("flow", "node"), ("node", 2.0), ("flow", "node", 2.0)],
        "condition": [std_func],
        RESPONSE.name.lower(): [Message(text="text"), std_func, None],
        pre_response_proc.name.lower(): [{}, {1: std_func}, None],
        PRE_TRANSITIONS_PROCESSING.name.lower(): [{}, {1: std_func}, None],
        MISC.name.lower(): [{}, {1: "var"}, None],
    }
    samples = [
        {
            TRANSITIONS.name.lower(): {transition: condition},
            RESPONSE.name.lower(): response,
            pre_response_proc.name.lower(): pre_response,
            PRE_TRANSITIONS_PROCESSING.name.lower(): pre_transitions,
            MISC.name.lower(): misc,
        }
        for transition, condition, response, pre_response, pre_transitions, misc in itertools.product(
            *list(samples.values())
        )
    ]
    samples = [{k: v for k, v in sample.items() if v is not None} for sample in samples]
    positive_test(samples, Node)

    samples = {
        "transition": [None],
        "condition": [None, 123, "asdasd", 2.0, [], {}],
        pre_response_proc.name.lower(): [123, "asdasd", 2.0, {1: None}, {1: 123}, {1: 2.0}, {1: []}, {1: {}}],
        PRE_TRANSITIONS_PROCESSING.name.lower(): [123, "asdasd", 2.0, {1: None}, {1: 123}, {1: 2.0}, {1: []}, {1: {}}],
        MISC.name.lower(): [123, "asdasd", 2.0],
    }
    samples = [
        {
            TRANSITIONS.name.lower(): {val if key == "transition" else "node": val if key == "condition" else std_func},
            RESPONSE.name.lower(): val if key == RESPONSE.name.lower() else None,
            pre_response_proc.name.lower(): val if key == pre_response_proc.name.lower() else None,
            PRE_TRANSITIONS_PROCESSING.name.lower(): val if key == PRE_TRANSITIONS_PROCESSING.name.lower() else None,
            MISC.name.lower(): val if key == MISC.name.lower() else None,
        }
        for key, values in samples.items()
        for val in values
    ]
    samples = [{k: v for k, v in sample.items() if v is not None} for sample in samples]
    negative_test(samples, Node)


def node_test(node: Node):
    assert list(node.transitions)[0] == ("", "node", float("-inf"))
    assert callable(list(node.transitions.values())[0])
    assert isinstance(node.pre_response_processing, dict)
    assert isinstance(node.pre_transitions_processing, dict)
    assert node.misc == {"key": "val"}


def test_node_exec():
    # node = Node(
    #     **{
    #         TRANSITIONS.name.lower(): {"node": std_func},
    #         RESPONSE.name.lower(): "text",
    #         PROCESSING.name.lower(): {1: std_func},
    #         PRE_TRANSITIONS_PROCESSING.name.lower(): {1: std_func},
    #         MISC.name.lower(): {"key": "val"},
    #     }
    # )
    # node_test(node)
    node = Node(
        **{
            TRANSITIONS.name.lower(): {"node": std_func},
            RESPONSE.name.lower(): Message(text="text"),
            PRE_RESPONSE_PROCESSING.name.lower(): {1: std_func},
            PRE_TRANSITIONS_PROCESSING.name.lower(): {1: std_func},
            MISC.name.lower(): {"key": "val"},
        }
    )
    node_test(node)


def test_script():
    script_test(PRE_RESPONSE_PROCESSING)


def script_test(pre_response_proc):
    node_template = {
        TRANSITIONS: {"node": std_func},
        RESPONSE: Message(text="text"),
        pre_response_proc: {1: std_func},
        PRE_TRANSITIONS_PROCESSING: {1: std_func},
        MISC: {"key": "val"},
    }
    script = Script(script={GLOBAL: node_template.copy(), "flow": {"node": node_template.copy()}})
    node_test(script[GLOBAL][GLOBAL])
    node_test(script["flow"]["node"])
    assert list(script.keys()) == [GLOBAL, "flow"]
    assert len(script.values()) == 2
    assert list(script) == [GLOBAL, "flow"]
    assert len(list(script.items())) == 2
