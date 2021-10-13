# %%
from typing import Callable

from dff.core.normalization import (
    normalize_condition,
    normalize_node_label,
    normalize_processing,
    normalize_response,
    normalize_transitions,
)


def std_func(ctx, actor, *args, **kwargs):
    pass


def test_normalize_node_label():
    # TODO: Add full check for functions
    assert isinstance(normalize_node_label(std_func), Callable)
    assert normalize_node_label("node", "flow") == ("flow", "node", float("-inf"))
    assert normalize_node_label(("flow", "node"), "flow") == ("flow", "node", float("-inf"))
    assert normalize_node_label(("flow", "node", 1.0), "flow") == ("flow", "node", 1.0)
    assert normalize_node_label(("node", 1.0), "flow") == ("flow", "node", 1.0)


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
