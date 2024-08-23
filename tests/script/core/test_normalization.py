# %%
from typing import Tuple

from chatsky.pipeline import Pipeline
from chatsky.script import (
    GLOBAL,
    TRANSITIONS,
    RESPONSE,
    MISC,
    PRE_RESPONSE_PROCESSING,
    PRE_TRANSITIONS_PROCESSING,
    Context,
    Script,
    Node,
    ConstLabel,
    Message,
)
from chatsky.script.labels import repeat
from chatsky.script.conditions import true

from chatsky.script.core.normalization import normalize_condition, normalize_label, normalize_response


def std_func(ctx, pipeline):
    pass


def create_env() -> Tuple[Context, Pipeline]:
    ctx = Context()
    script = {"flow": {"node1": {TRANSITIONS: {repeat(): true()}, RESPONSE: Message("response")}}}
    pipeline = Pipeline(script=script, start_label=("flow", "node1"), fallback_label=("flow", "node1"))
    ctx.add_request(Message("text"))
    return ctx, pipeline


def test_normalize_label():
    ctx, actor = create_env()

    def true_label_func(ctx: Context, pipeline: Pipeline) -> ConstLabel:
        return ("flow", "node1", 1)

    def false_label_func(ctx: Context, pipeline: Pipeline) -> ConstLabel:
        return ("flow", "node2", 1)

    n_f = normalize_label(true_label_func)
    assert callable(n_f)
    assert n_f(ctx, actor) == ("flow", "node1", 1)
    n_f = normalize_label(false_label_func)
    assert n_f(ctx, actor) is None

    assert normalize_label("node", "flow") == ("flow", "node", float("-inf"))
    assert normalize_label(("flow", "node"), "flow") == ("flow", "node", float("-inf"))
    assert normalize_label(("flow", "node", 1.0), "flow") == ("flow", "node", 1.0)
    assert normalize_label(("node", 1.0), "flow") == ("flow", "node", 1.0)


def test_normalize_condition():
    ctx, actor = create_env()

    def true_condition_func(ctx: Context, pipeline: Pipeline) -> bool:
        return True

    def false_condition_func(ctx: Context, pipeline: Pipeline) -> bool:
        raise Exception("False condition")

    n_f = normalize_condition(true_condition_func)
    assert callable(n_f)
    flag = n_f(ctx, actor)
    assert isinstance(flag, bool) and flag
    n_f = normalize_condition(false_condition_func)
    flag = n_f(ctx, actor)
    assert isinstance(flag, bool) and not flag

    assert callable(normalize_condition(std_func))


def test_normalize_transitions():
    trans = Node.normalize_transitions({("flow", "node", 1.0): std_func})
    assert list(trans)[0] == ("flow", "node", 1.0)
    assert callable(list(trans.values())[0])


def test_normalize_response():
    assert callable(normalize_response(std_func))
    assert callable(normalize_response(Message("text")))


def test_normalize_keywords():
    node_template = {
        TRANSITIONS: {"node": std_func},
        RESPONSE: Message("text"),
        PRE_RESPONSE_PROCESSING: {1: std_func},
        PRE_TRANSITIONS_PROCESSING: {1: std_func},
        MISC: {"key": "val"},
    }
    node_template_gold = {
        TRANSITIONS.name.lower(): {"node": std_func},
        RESPONSE.name.lower(): Message("text"),
        PRE_RESPONSE_PROCESSING.name.lower(): {1: std_func},
        PRE_TRANSITIONS_PROCESSING.name.lower(): {1: std_func},
        MISC.name.lower(): {"key": "val"},
    }
    script = {"flow": {"node": node_template.copy()}}
    assert isinstance(script, dict)
    assert script["flow"]["node"] == node_template_gold


def test_normalize_script():
    # TODO: Add full check for functions
    node_template = {
        TRANSITIONS: {"node": std_func},
        RESPONSE: Message("text"),
        PRE_RESPONSE_PROCESSING: {1: std_func},
        PRE_TRANSITIONS_PROCESSING: {1: std_func},
        MISC: {"key": "val"},
    }
    node_template_gold = {
        TRANSITIONS.name.lower(): {"node": std_func},
        RESPONSE.name.lower(): Message("text"),
        PRE_RESPONSE_PROCESSING.name.lower(): {1: std_func},
        PRE_TRANSITIONS_PROCESSING.name.lower(): {1: std_func},
        MISC.name.lower(): {"key": "val"},
    }
    script = {GLOBAL: node_template.copy(), "flow": {"node": node_template.copy()}}
    script = Script.normalize_script(script)
    assert isinstance(script, dict)
    assert script[GLOBAL][GLOBAL] == node_template_gold
    assert script["flow"]["node"] == node_template_gold
