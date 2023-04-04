# %%
from dff.pipeline import Pipeline
from dff.script import (
    TRANSITIONS,
    RESPONSE,
    GLOBAL,
    LOCAL,
    PRE_TRANSITIONS_PROCESSING,
    PRE_RESPONSE_PROCESSING,
    Context,
    Message,
)
from dff.script.conditions import true
from dff.script.labels import repeat


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


def fake_label(ctx: Context, actor, *args, **kwargs):
    if not ctx.validation:
        return ("123", "123", 0)
    return ("flow", "node1", 1)


def raised_response(ctx: Context, actor, *args, **kwargs):
    raise Exception("")


def test_actor():
    try:
        # fail of start label
        Pipeline.from_script({"flow": {"node1": {}}}, start_label=("flow1", "node1"))
        raise Exception("can not be passed: fail of start label")
    except ValueError:
        pass
    try:
        # fail of fallback label
        Pipeline.from_script({"flow": {"node1": {}}}, start_label=("flow", "node1"), fallback_label=("flow1", "node1"))
        raise Exception("can not be passed: fail of fallback label")
    except ValueError:
        pass
    try:
        # fail of missing node
        Pipeline.from_script({"flow": {"node1": {TRANSITIONS: {"miss_node1": true()}}}}, start_label=("flow", "node1"))
        raise Exception("can not be passed: fail of missing node")
    except ValueError:
        pass
    try:
        # fail of condition returned type
        Pipeline.from_script({"flow": {"node1": {TRANSITIONS: {"node1": std_func}}}}, start_label=("flow", "node1"))
        raise Exception("can not be passed: fail of condition returned type")
    except ValueError:
        pass
    try:
        # fail of response returned Callable
        pipeline = Pipeline.from_script(
            {"flow": {"node1": {RESPONSE: lambda c, a: lambda x: 1, TRANSITIONS: {repeat(): true()}}}},
            start_label=("flow", "node1"),
        )
        ctx = Context()
        pipeline.actor(pipeline, ctx)
        raise Exception("can not be passed: fail of response returned Callable")
    except ValueError:
        pass
    try:
        # failed response
        Pipeline.from_script(
            {"flow": {"node1": {RESPONSE: raised_response, TRANSITIONS: {repeat(): true()}}}},
            start_label=("flow", "node1"),
        )
        raise Exception("can not be passed: failed response")
    except ValueError:
        pass

    # empty ctx stability
    pipeline = Pipeline.from_script(
        {"flow": {"node1": {TRANSITIONS: {"node1": true()}}}}, start_label=("flow", "node1")
    )
    ctx = Context()
    pipeline.actor(pipeline, ctx)

    # fake label stability
    pipeline = Pipeline.from_script(
        {"flow": {"node1": {TRANSITIONS: {fake_label: true()}}}}, start_label=("flow", "node1")
    )
    ctx = Context()
    pipeline.actor(pipeline, ctx)


limit_errors = {}


def check_call_limit(limit: int = 1, default_value=None, label=""):
    counter = 0

    def call_limit_handler(ctx: Context, actor, *args, **kwargs):
        nonlocal counter
        counter += 1
        if counter > limit:
            msg = f"calls are out of limits counterlimit={counter}/{limit} for {default_value} and {label}"
            limit_errors[call_limit_handler] = msg
        if default_value == "ctx":
            return ctx
        return default_value

    return call_limit_handler


def test_call_limit():
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
                RESPONSE: check_call_limit(1, Message(text="r1"), "flow1_node1"),
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
                RESPONSE: check_call_limit(1, Message(text="r1"), "flow1_node2"),
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
                RESPONSE: check_call_limit(1, Message(text="r1"), "flow2_node1"),
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
                RESPONSE: check_call_limit(1, Message(text="r1"), "flow2_node2"),
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
    ctx = Context()
    pipeline = Pipeline.from_script(script=script, start_label=("flow1", "node1"), validation_stage=False)
    for i in range(4):
        ctx.add_request(Message(text="req1"))
        ctx = pipeline.actor(pipeline, ctx)
    if limit_errors:
        error_msg = repr(limit_errors)
        raise Exception(error_msg)


if __name__ == "__main__":
    test_call_limit()
