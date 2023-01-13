# %%
from typing import Callable

from dff.script import (
    GLOBAL,
    TRANSITIONS,
    RESPONSE,
    MISC,
    PRE_RESPONSE_PROCESSING,
    PRE_TRANSITIONS_PROCESSING,
    Actor,
    Context,
    NodeLabel3Type,
    Message,
)
from dff.script.labels import repeat
from dff.script.conditions import true

from dff.script import (
    normalize_condition,
    normalize_keywords,
    normalize_label,
    normalize_script,
    normalize_processing,
    normalize_response,
    normalize_transitions,
)


def std_func(ctx, actor, *args, **kwargs):
    pass


def create_env():
    ctx = Context()
    script = {"flow": {"node1": {TRANSITIONS: {repeat(): true()}, RESPONSE: Message(text="response")}}}
    actor = Actor(script=script, start_label=("flow", "node1"), fallback_label=("flow", "node1"))
    ctx.add_request(Message(text="text"))
    return ctx, actor


def test_normalize_label():
    ctx, actor = create_env()

    def true_label_func(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        return ("flow", "node1", 1)

    def false_label_func(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        return ("flow", "node2", 1)

    n_f = normalize_label(true_label_func)
    assert isinstance(n_f, Callable)
    assert n_f(ctx, actor) == ("flow", "node1", 1)
    n_f = normalize_label(false_label_func)
    assert n_f(ctx, actor) is None

    assert normalize_label("node", "flow") == ("flow", "node", float("-inf"))
    assert normalize_label(("flow", "node"), "flow") == ("flow", "node", float("-inf"))
    assert normalize_label(("flow", "node", 1.0), "flow") == ("flow", "node", 1.0)
    assert normalize_label(("node", 1.0), "flow") == ("flow", "node", 1.0)


def test_normalize_condition():
    ctx, actor = create_env()

    def true_condition_func(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return True

    def false_condition_func(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        raise Exception("False condition")

    n_f = normalize_condition(true_condition_func)
    assert isinstance(n_f, Callable)
    flag = n_f(ctx, actor)
    assert isinstance(flag, bool) and flag
    n_f = normalize_condition(false_condition_func)
    flag = n_f(ctx, actor)
    assert isinstance(flag, bool) and not flag

    assert isinstance(normalize_condition(std_func), Callable)


def test_normalize_transitions():
    trans = normalize_transitions({("flow", "node", 1.0): std_func})
    assert list(trans)[0] == ("flow", "node", 1.0)
    assert isinstance(list(trans.values())[0], Callable)


def test_normalize_response():
    assert isinstance(normalize_response(std_func), Callable)
    assert isinstance(normalize_response(Message(text="text")), Callable)


def test_normalize_processing():
    ctx, actor = create_env()

    def true_processing_func(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
        return ctx

    def false_processing_func(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
        raise Exception("False processing")

    n_f = normalize_processing({1: true_processing_func})
    assert isinstance(n_f, Callable)
    assert isinstance(n_f(ctx, actor), Context)
    n_f = normalize_processing({1: false_processing_func})
    assert isinstance(n_f(ctx, actor), Context)

    # TODO: Add full check for functions
    assert isinstance(normalize_processing({}), Callable)
    assert isinstance(normalize_processing({1: std_func}), Callable)
    assert isinstance(normalize_processing({1: std_func, 2: std_func}), Callable)


def test_normalize_keywords():
    # TODO: Add full check for functions
    subtest_normalize_keywords(PRE_RESPONSE_PROCESSING)


def subtest_normalize_keywords(pre_response_processing):
    # TODO: Add full check for functions
    node_template = {
        TRANSITIONS: {"node": std_func},
        RESPONSE: Message(text="text"),
        pre_response_processing: {1: std_func},
        PRE_TRANSITIONS_PROCESSING: {1: std_func},
        MISC: {"key": "val"},
    }
    node_template_gold = {
        TRANSITIONS.name.lower(): {"node": std_func},
        RESPONSE.name.lower(): Message(text="text"),
        PRE_RESPONSE_PROCESSING.name.lower(): {1: std_func},
        PRE_TRANSITIONS_PROCESSING.name.lower(): {1: std_func},
        MISC.name.lower(): {"key": "val"},
    }
    script = {"flow": {"node": node_template.copy()}}
    script = normalize_keywords(script)
    assert isinstance(script, dict)
    assert script["flow"]["node"] == node_template_gold


def test_normalize_script():
    # TODO: Add full check for functions
    node_template = {
        TRANSITIONS: {"node": std_func},
        RESPONSE: Message(text="text"),
        PRE_RESPONSE_PROCESSING: {1: std_func},
        PRE_TRANSITIONS_PROCESSING: {1: std_func},
        MISC: {"key": "val"},
    }
    node_template_gold = {
        TRANSITIONS.name.lower(): {"node": std_func},
        RESPONSE.name.lower(): Message(text="text"),
        PRE_RESPONSE_PROCESSING.name.lower(): {1: std_func},
        PRE_TRANSITIONS_PROCESSING.name.lower(): {1: std_func},
        MISC.name.lower(): {"key": "val"},
    }
    script = {GLOBAL: node_template.copy(), "flow": {"node": node_template.copy()}}
    script = normalize_script(script)
    assert isinstance(script, dict)
    assert script[GLOBAL][GLOBAL] == node_template_gold
    assert script["flow"]["node"] == node_template_gold
