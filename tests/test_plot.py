# %%
import itertools
from typing import Callable


from df_engine.core import Plot, Node
from df_engine.core.keywords import GLOBAL, TRANSITIONS, RESPONSE, PROCESSING, MISC


def positive_test(samples, custom_class):
    results = []
    for sample in samples:
        try:
            res = custom_class(**sample)
            results += [res]
        except Exception as exeption:
            raise Exception(f"{sample=} gets {exeption=}")
    return results


def negative_test(samples, custom_class):
    for sample in samples:
        try:
            custom_class(**sample)
        except Exception:  # TODO: spetial tyupe of exceptions
            continue
        raise Exception(f"{sample=} can not be passed")


def std_func(ctx, actor, *args, **kwargs):
    pass


def test_node_creation():

    samples = {
        "transition": [std_func, "node", ("flow", "node"), ("node", 2.0), ("flow", "node", 2.0)],
        "condition": [std_func],
        RESPONSE.name.lower(): ["text", std_func, 123, 1.0, None],
        PROCESSING.name.lower(): [{}, {1: std_func}, None],
        MISC.name.lower(): [{}, {1: "var"}, None],
    }
    samples = [
        {
            TRANSITIONS.name.lower(): {transition: condition},
            RESPONSE.name.lower(): response,
            PROCESSING.name.lower(): processing,
            MISC.name.lower(): misc,
        }
        for transition, condition, response, processing, misc in itertools.product(*list(samples.values()))
    ]
    samples = [{k: v for k, v in sample.items() if v is not None} for sample in samples]
    positive_test(samples, Node)

    samples = {
        "transition": [None],
        "condition": [None, 123, "asdasd", 2.0, [], {}],
        PROCESSING.name.lower(): [123, "asdasd", 2.0, {1: None}, {1: 123}, {1: 2.0}, {1: []}, {1: {}}],
        MISC.name.lower(): [123, "asdasd", 2.0],
    }
    samples = [
        {
            TRANSITIONS.name.lower(): {val if key == "transition" else "node": val if key == "condition" else std_func},
            RESPONSE.name.lower(): val if key == RESPONSE.name.lower() else None,
            PROCESSING.name.lower(): val if key == PROCESSING.name.lower() else None,
            MISC.name.lower(): val if key == MISC.name.lower() else None,
        }
        for key, values in samples.items()
        for val in values
    ]
    samples = [{k: v for k, v in sample.items() if v is not None} for sample in samples]
    negative_test(samples, Node)


def node_test(node):
    assert list(node.transitions)[0] == ("", "node", float("-inf"))
    assert isinstance(list(node.transitions.values())[0], Callable)
    assert isinstance(node.processing, dict)
    assert node.misc == {"key": "val"}


def test_node_exec():
    node = Node(
        **{
            TRANSITIONS.name.lower(): {"node": std_func},
            RESPONSE.name.lower(): "text",
            PROCESSING.name.lower(): {1: std_func},
            MISC.name.lower(): {"key": "val"},
        }
    )
    node_test(node)


def test_plot():
    node_template = {TRANSITIONS: {"node": std_func}, RESPONSE: "text", PROCESSING: {1: std_func}, MISC: {"key": "val"}}
    plot = Plot(plot={GLOBAL: node_template.copy(), "flow": {"node": node_template.copy()}})
    node_test(plot[GLOBAL][GLOBAL])
    node_test(plot["flow"]["node"])
    assert list(plot.keys()) == [GLOBAL, "flow"]
    assert len(plot.values()) == 2
    assert list(plot) == [GLOBAL, "flow"]
    assert len(list(plot.items())) == 2
