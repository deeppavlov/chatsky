import asyncio

import pytest

from chatsky.core import BaseProcessing, BaseResponse, Pipeline
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.service.actor import Actor, logger
from chatsky.core.message import Message, MessageInitTypes
from chatsky.core.context import Context
from chatsky.core.script import Script
from chatsky.core.keywords import RESPONSE, TRANSITIONS, PRE_TRANSITION, PRE_RESPONSE


class TestRequestProcessing:
    async def test_normal_execution(self):
        script = Script.model_validate({"flow": {
            "node1": {
                RESPONSE: "node1",
                TRANSITIONS: [{"dst": "node2"}]
            },
            "node2": {
                RESPONSE: "node2",
                TRANSITIONS: [{"dst": "node3"}]
            },
            "node3": {
                RESPONSE: "node3"
            },
            "fallback": {
                RESPONSE: "fallback"
            }
        }})

        ctx = Context.init(start_label=("flow", "node1"))
        actor = Actor()
        ctx.framework_data.pipeline = Pipeline(
            parallelize_processing=True,
            script=script,
            fallback_label=AbsoluteNodeLabel(flow_name="flow", node_name="fallback"),
            start_label=("flow", "node1")
        )

        await actor(ctx, ctx.framework_data.pipeline)

        assert ctx.labels == {
            -1: AbsoluteNodeLabel(flow_name="flow", node_name="node1"),
            0: AbsoluteNodeLabel(flow_name="flow", node_name="node2")
        }
        assert ctx.responses == {0: Message("node2")}

    async def test_fallback_node(self):
        script = Script.model_validate({
            "flow": {"node": {}, "fallback": {RESPONSE: "fallback"}}
        })

        ctx = Context.init(start_label=("flow", "node"))
        actor = Actor()
        ctx.framework_data.pipeline = Pipeline(
            parallelize_processing=True,
            script=script,
            fallback_label=AbsoluteNodeLabel(flow_name="flow", node_name="fallback"),
            start_label=("flow", "node")
        )

        await actor(ctx, ctx.framework_data.pipeline)

        assert ctx.labels == {
            -1: AbsoluteNodeLabel(flow_name="flow", node_name="node"),
            0: AbsoluteNodeLabel(flow_name="flow", node_name="fallback")
        }
        assert ctx.responses == {0: Message("fallback")}

    @pytest.mark.parametrize("default_priority,result", [
        (1, "node3"),
        (2, "node2"),
        (3, "node2"),
    ])
    async def test_default_priority(self, default_priority, result):
        script = Script.model_validate({
            "flow": {"node1": {
                TRANSITIONS: [{"dst": "node2"}, {"dst": "node3", "priority": 2}]
            }, "node2": {}, "node3": {}, "fallback": {}}
        })

        ctx = Context.init(start_label=("flow", "node1"))
        actor = Actor()
        ctx.framework_data.pipeline = Pipeline(
            parallelize_processing=True,
            script=script,
            fallback_label=AbsoluteNodeLabel(flow_name="flow", node_name="fallback"),
            default_priority=default_priority,
            start_label=("flow", "node1")
        )

        await actor(ctx, ctx.framework_data.pipeline)
        assert ctx.last_label.node_name == result

    async def test_transition_exception_handling(self, log_event_catcher):
        log_list = log_event_catcher(logger, level="ERROR")

        class MyProcessing(BaseProcessing):
            async def call(self, ctx: Context) -> None:
                ctx.framework_data.current_node = None

        script = Script.model_validate({"flow": {"node": {PRE_TRANSITION: {"": MyProcessing()}}, "fallback": {}}})

        ctx = Context.init(start_label=("flow", "node"))
        actor = Actor()
        ctx.framework_data.pipeline = Pipeline(
            parallelize_processing=True,
            script=script,
            fallback_label=AbsoluteNodeLabel(flow_name="flow", node_name="fallback"),
            start_label=("flow", "node")
        )

        await actor(ctx, ctx.framework_data.pipeline)

        assert ctx.last_label.node_name == "fallback"
        assert log_list[0].msg == "Exception occurred during transition processing."
        assert str(log_list[0].exc_info[1]) == "Current node is not set."

    async def test_empty_response(self, log_event_catcher):
        log_list = log_event_catcher(logger, level="DEBUG")

        script = Script.model_validate({"flow": {"node": {}}})

        ctx = Context.init(start_label=("flow", "node"))
        actor = Actor()
        ctx.framework_data.pipeline = Pipeline(
            parallelize_processing=True,
            script=script,
            fallback_label=AbsoluteNodeLabel(flow_name="flow", node_name="node"),
            start_label=("flow", "node")
        )

        await actor(ctx, ctx.framework_data.pipeline)

        assert ctx.responses == {0: Message()}
        assert log_list[-1].msg == "Node has empty response."

    async def test_bad_response(self, log_event_catcher):
        log_list = log_event_catcher(logger, level="DEBUG")

        class MyResponse(BaseResponse):
            async def call(self, ctx: Context) -> MessageInitTypes:
                return None

        script = Script.model_validate({"flow": {"node": {RESPONSE: MyResponse()}}})

        ctx = Context.init(start_label=("flow", "node"))
        actor = Actor()
        ctx.framework_data.pipeline = Pipeline(
            parallelize_processing=True,
            script=script,
            fallback_label=AbsoluteNodeLabel(flow_name="flow", node_name="node"),
            start_label=("flow", "node")
        )

        await actor(ctx, ctx.framework_data.pipeline)

        assert ctx.responses == {0: Message()}
        assert log_list[-1].msg == "Response was not produced."

    async def test_response_exception_handling(self, log_event_catcher):
        log_list = log_event_catcher(logger, level="ERROR")

        class MyProcessing(BaseProcessing):
            async def call(self, ctx: Context) -> None:
                ctx.framework_data.current_node = None

        script = Script.model_validate({"flow": {"node": {PRE_RESPONSE: {"": MyProcessing()}}}})

        ctx = Context.init(start_label=("flow", "node"))
        actor = Actor()
        ctx.framework_data.pipeline = Pipeline(
            parallelize_processing=True,
            script=script,
            fallback_label=AbsoluteNodeLabel(flow_name="flow", node_name="node"),
            start_label=("flow", "node")
        )

        await actor(ctx, ctx.framework_data.pipeline)

        assert ctx.responses == {0: Message()}
        assert log_list[0].msg == "Exception occurred during response processing."
        assert str(log_list[0].exc_info[1]) == "Current node is not set."


async def test_pre_processing():
    contested_resource = {}

    class Proc1(BaseProcessing):
        async def call(self, ctx: Context) -> None:
            await asyncio.sleep(0)
            contested_resource[""] = 1

    class Proc2(BaseProcessing):
        async def call(self, ctx: Context) -> None:
            contested_resource[""] = 2

    procs = {"1": Proc1(), "2": Proc2()}

    ctx = Context.init(start_label=("flow", "node"))

    ctx.framework_data.pipeline = Pipeline(
        parallelize_processing=True,
        script={"": {"": {}}},
        start_label=("", "")
    )
    await Actor._run_processing(procs, ctx)
    assert contested_resource[""] == 1

    ctx.framework_data.pipeline = Pipeline(
        parallelize_processing=False,
        script={"": {"": {}}},
        start_label=("", "")
    )
    await Actor._run_processing(procs, ctx)
    assert contested_resource[""] == 2
