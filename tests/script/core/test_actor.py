# %%
import pytest
from chatsky.pipeline import Pipeline, ComponentExecutionState
from chatsky.script import (
    TRANSITIONS,
    RESPONSE,
    GLOBAL,
    LOCAL,
    PRE_TRANSITIONS_PROCESSING,
    PRE_RESPONSE_PROCESSING,
    Context,
    Message,
)
from chatsky.script.conditions import true
from chatsky.script.labels import repeat


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


def std_func(ctx, pipeline):
    pass


def fake_label(ctx: Context, pipeline):
    return ("flow", "node1", 1)


def raised_response(ctx: Context, pipeline):
    raise Exception("")


@pytest.mark.asyncio
async def test_actor():
    try:
        # fail of start label
        Pipeline(script={"flow": {"node1": {}}}, start_label=("flow1", "node1"))
        raise Exception("can not be passed: fail of start label")
    except ValueError:
        pass
    try:
        # fail of fallback label
        Pipeline(script={"flow": {"node1": {}}}, start_label=("flow", "node1"), fallback_label=("flow1", "node1"))
        raise Exception("can not be passed: fail of fallback label")
    except ValueError:
        pass
    try:
        # fail of missing node
        Pipeline(script={"flow": {"node1": {TRANSITIONS: {"miss_node1": true()}}}}, start_label=("flow", "node1"))
        raise Exception("can not be passed: fail of missing node")
    except ValueError:
        pass
    try:
        # fail of response returned Callable
        pipeline = Pipeline(
            script={"flow": {"node1": {RESPONSE: lambda c, a: lambda x: 1, TRANSITIONS: {repeat(): true()}}}},
            start_label=("flow", "node1"),
        )
        ctx = Context()
        await pipeline.actor(ctx, pipeline)
        assert pipeline.actor.get_state(ctx) is not ComponentExecutionState.FAILED
        raise Exception("can not be passed: fail of response returned Callable")
    except AssertionError:
        pass

    # empty ctx stability
    pipeline = Pipeline(script={"flow": {"node1": {TRANSITIONS: {"node1": true()}}}}, start_label=("flow", "node1"))
    ctx = Context()
    await pipeline.actor(ctx, pipeline)

    # fake label stability
    pipeline = Pipeline(script={"flow": {"node1": {TRANSITIONS: {fake_label: true()}}}}, start_label=("flow", "node1"))
    ctx = Context()
    await pipeline.actor(ctx, pipeline)


limit_errors = {}


def check_call_limit(limit: int = 1, default_value=None, label=""):
    counter = 0

    def call_limit_handler(ctx: Context, pipeline):
        nonlocal counter
        counter += 1
        if counter > limit:
            msg = f"calls are out of limits counterlimit={counter}/{limit} for {default_value} and {label}"
            limit_errors[call_limit_handler] = msg
        if default_value == "ctx":
            return ctx
        return default_value

    return call_limit_handler


@pytest.mark.asyncio
async def test_call_limit():
    script = {
        GLOBAL: {
            TRANSITIONS: {
                check_call_limit(4, ("flow1", "node1", 0.0), "global label"): check_call_limit(4, True, "global cond")
            },
            PRE_TRANSITIONS_PROCESSING: {"tpg": check_call_limit(4, "ctx", "tpg")},
            PRE_RESPONSE_PROCESSING: {"rpg": check_call_limit(4, "ctx", "rpg")},
        },
        "flow1": {
            LOCAL: {
                TRANSITIONS: {
                    check_call_limit(2, ("flow1", "node1", 0.0), "local label for flow1"): check_call_limit(
                        2, True, "local cond for flow1"
                    )
                },
                PRE_TRANSITIONS_PROCESSING: {"tpl": check_call_limit(2, "ctx", "tpl")},
                PRE_RESPONSE_PROCESSING: {"rpl": check_call_limit(3, "ctx", "rpl")},
            },
            "node1": {
                RESPONSE: check_call_limit(1, Message("r1"), "flow1_node1"),
                PRE_TRANSITIONS_PROCESSING: {"tp1": check_call_limit(1, "ctx", "flow1_node1_tp1")},
                TRANSITIONS: {
                    check_call_limit(1, ("flow1", "node2"), "cond flow1_node2"): check_call_limit(
                        1,
                        True,
                        "cond flow1_node2",
                    )
                },
                PRE_RESPONSE_PROCESSING: {"rp1": check_call_limit(1, "ctx", "flow1_node1_rp1")},
            },
            "node2": {
                RESPONSE: check_call_limit(1, Message("r1"), "flow1_node2"),
                PRE_TRANSITIONS_PROCESSING: {"tp1": check_call_limit(1, "ctx", "flow1_node2_tp1")},
                TRANSITIONS: {
                    check_call_limit(1, ("flow2", "node1"), "cond flow2_node1"): check_call_limit(
                        1,
                        True,
                        "cond flow2_node1",
                    )
                },
                PRE_RESPONSE_PROCESSING: {"rp1": check_call_limit(1, "ctx", "flow1_node2_rp1")},
            },
        },
        "flow2": {
            LOCAL: {
                TRANSITIONS: {
                    check_call_limit(2, ("flow1", "node1", 0.0), "local label for flow2"): check_call_limit(
                        2, True, "local cond for flow2"
                    )
                },
                PRE_TRANSITIONS_PROCESSING: {"tpl": check_call_limit(2, "ctx", "tpl")},
                PRE_RESPONSE_PROCESSING: {"rpl": check_call_limit(2, "ctx", "rpl")},
            },
            "node1": {
                RESPONSE: check_call_limit(1, Message("r1"), "flow2_node1"),
                PRE_TRANSITIONS_PROCESSING: {"tp1": check_call_limit(1, "ctx", "flow2_node1_tp1")},
                TRANSITIONS: {
                    check_call_limit(1, ("flow2", "node2"), "label flow2_node2"): check_call_limit(
                        1,
                        True,
                        "cond flow2_node2",
                    )
                },
                PRE_RESPONSE_PROCESSING: {"rp1": check_call_limit(1, "ctx", "flow2_node1_rp1")},
            },
            "node2": {
                RESPONSE: check_call_limit(1, Message("r1"), "flow2_node2"),
                PRE_TRANSITIONS_PROCESSING: {"tp1": check_call_limit(1, "ctx", "flow2_node2_tp1")},
                TRANSITIONS: {
                    check_call_limit(1, ("flow1", "node1"), "label flow2_node2"): check_call_limit(
                        1,
                        True,
                        "cond flow2_node2",
                    )
                },
                PRE_RESPONSE_PROCESSING: {"rp1": check_call_limit(1, "ctx", "flow2_node2_rp1")},
            },
        },
    }
    # script = {"flow": {"node1": {TRANSITIONS: {"node1": true()}}}}
    pipeline = Pipeline(script=script, start_label=("flow1", "node1"))
    for i in range(4):
        await pipeline._run_pipeline(Message("req1"), 0)
    if limit_errors:
        error_msg = repr(limit_errors)
        raise Exception(error_msg)
