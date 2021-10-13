# %%
from typing import Callable

from dff.core.keywords import GLOBAL, TRANSITIONS, RESPONSE, PROCESSING, MISC
from dff.core.normalization import (
    normalize_condition,
    normalize_label,
    normalize_plot,
    normalize_processing,
    normalize_response,
    normalize_transitions,
)


def std_func(ctx, actor, *args, **kwargs):
    pass


def test_normalize_label():
    # TODO: Add full check for functions
    assert isinstance(normalize_label(std_func), Callable)
    assert normalize_label("node", "flow") == ("flow", "node", float("-inf"))
    assert normalize_label(("flow", "node"), "flow") == ("flow", "node", float("-inf"))
    assert normalize_label(("flow", "node", 1.0), "flow") == ("flow", "node", 1.0)
    assert normalize_label(("node", 1.0), "flow") == ("flow", "node", 1.0)


def test_normalize_condition():
    # TODO: Add full check for functions
    assert isinstance(normalize_condition(std_func), Callable)


def test_normalize_transitions():
    # TODO: Add full check for functions
    trans = normalize_transitions({("flow", "node", 1.0): std_func})
    assert list(trans)[0] == ("flow", "node", 1.0)
    assert isinstance(list(trans.values())[0], Callable)


def test_normalize_response():
    # TODO: Add full check for functions
    assert isinstance(normalize_response(std_func), Callable)
    assert isinstance(normalize_response(123), Callable)
    assert isinstance(normalize_response("text"), Callable)
    assert isinstance(normalize_response({"k": "v"}), Callable)
    assert isinstance(normalize_response(["v"]), Callable)


def test_normalize_processing():
    # TODO: Add full check for functions
    assert isinstance(normalize_processing({}), Callable)
    assert isinstance(normalize_processing({1: std_func}), Callable)
    assert isinstance(normalize_processing({1: std_func, 2: std_func}), Callable)


def test_normalize_plot():
    # TODO: Add full check for functions
    node_template = {
        TRANSITIONS: {"node": std_func},
        RESPONSE: "text",
        PROCESSING: {1: std_func},
        MISC: {"key": "val"},
    }
    plot = {
        GLOBAL: node_template.copy(),
        "flow": {"node": node_template.copy()},
    }
    plot = normalize_plot(plot)
    assert isinstance(plot, dict)
    assert plot[GLOBAL][GLOBAL] == node_template
    assert plot["flow"]["node"] == node_template
