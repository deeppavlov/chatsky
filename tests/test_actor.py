# %%

from df_engine.core import Actor
from df_engine.core.context import Context
from df_engine.core.keywords import TRANSITIONS, RESPONSE
from df_engine.conditions import true
from df_engine.labels import repeat


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


def fake_label(ctx: Context, actor, *args, **kwargs):
    if not ctx.validation:
        return ("123", "123", 0)
    return ("flow", "node1", 1)


def raised_response(ctx: Context, actor, *args, **kwargs):
    raise Exception("")


def test_actor():
    try:
        # fail of start label
        Actor({"flow": {"node1": {}}}, start_label=("flow1", "node1"))
        raise Exception("can not be passed")
    except ValueError:
        pass
    try:
        # fail of fallback label
        Actor({"flow": {"node1": {}}}, start_label=("flow", "node1"), fallback_label=("flow1", "node1"))
        raise Exception("can not be passed")
    except ValueError:
        pass
    try:
        # fail of missing node
        Actor({"flow": {"node1": {TRANSITIONS: {"miss_node1": true()}}}}, start_label=("flow", "node1"))
        raise Exception("can not be passed")
    except ValueError:
        pass
    try:
        # fail of condition returned type
        Actor({"flow": {"node1": {TRANSITIONS: {"node1": std_func}}}}, start_label=("flow", "node1"))
        raise Exception("can not be passed")
    except ValueError:
        pass
    try:
        # fail of response reterned Callable
        actor = Actor(
            {"flow": {"node1": {RESPONSE: lambda c, a: lambda x: 1, TRANSITIONS: {repeat(): true()}}}},
            start_label=("flow", "node1"),
        )
        ctx = Context()
        actor(ctx)
        raise Exception("can not be passed")
    except ValueError:
        pass
    try:
        # failed response
        actor = Actor(
            {"flow": {"node1": {RESPONSE: raised_response, TRANSITIONS: {repeat(): true()}}}},
            start_label=("flow", "node1"),
        )
        raise Exception("can not be passed")
    except ValueError:
        pass

    # empty ctx stability
    actor = Actor({"flow": {"node1": {TRANSITIONS: {"node1": true()}}}}, start_label=("flow", "node1"))
    ctx = Context()
    actor(ctx)

    # fake label stability
    actor = Actor({"flow": {"node1": {TRANSITIONS: {fake_label: true()}}}}, start_label=("flow", "node1"))
    ctx = Context()
    actor(ctx)
