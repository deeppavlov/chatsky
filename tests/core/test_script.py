import pytest

from chatsky.core import Transition as Tr, BaseProcessing, Context, AbsoluteNodeLabel
import chatsky.conditions as cnd
import chatsky.destinations as dst
import chatsky.responses as rsp
from chatsky.core.script import Node, Flow, Script


class MyProcessing(BaseProcessing):
    value: str = ""

    async def call(self, ctx: Context) -> None:
        return


@pytest.mark.parametrize(
    "first,second,result",
    [
        (
            Node(transitions=[Tr(dst="node1"), Tr(dst="node2")]),
            Node(transitions=[Tr(dst="node3"), Tr(dst="node4")]),
            Node(transitions=[Tr(dst="node3"), Tr(dst="node4"), Tr(dst="node1"), Tr(dst="node2")]),
        ),
        (
            Node(response="msg1"),
            Node(response="msg2"),
            Node(response="msg2"),
        ),
        (
            Node(response="msg1"),
            Node(),
            Node(response="msg1"),
        ),
        (
            Node(
                pre_response={"key": MyProcessing(value="1")},
                pre_transition={"key": MyProcessing(value="3")},
                misc={"k1": "v1"}
            ),
            Node(
                pre_response={"key": MyProcessing(value="2")},
                pre_transition={},
                misc={"k2": "v2"}
            ),
            Node(
                pre_response={"key": MyProcessing(value="2")},
                pre_transition={"key": MyProcessing(value="3")},
                misc={"k1": "v1", "k2": "v2"}
            ),
        ),
    ]
)
def test_node_merge(first, second, result):
    assert first.merge(second) == result


def test_flow_get_node():
    flow = Flow(node1=Node(response="text"))

    assert flow.get_node("node1") == Node(response="text")
    assert flow.get_node("node2") is None


def test_script_get_methods():
    flow = Flow(node1=Node(response="text"))
    script = Script(flow1=flow)

    assert script.get_flow("flow1") == flow
    assert script.get_flow("flow2") is None

    assert script.get_node(AbsoluteNodeLabel(flow_name="flow1", node_name="node1")) == Node(response="text")
    assert script.get_node(AbsoluteNodeLabel(flow_name="flow1", node_name="node2")) is None
    assert script.get_node(AbsoluteNodeLabel(flow_name="flow2", node_name="node1")) is None


def test_get_inherited_node():
    global_node = Node(
        misc={"k1": "g1", "k2": "g2", "k3": "g3"}
    )
    local_node = Node(
        misc={"k2": "l1", "k3": "l2", "k4": "l3"}
    )
    node = Node(
        misc={"k3": "n1", "k4": "n2", "k5": "n3"}
    )
    script = Script.model_validate(
        {
            "global": global_node,
            "flow": {
                "local": local_node,
                "node": node
            }
        }
    )

    assert script.get_global_local_inherited_node(AbsoluteNodeLabel(flow_name="", node_name="")) == None
    assert script.get_global_local_inherited_node(AbsoluteNodeLabel(flow_name="flow", node_name="")) == None
    assert script.get_global_local_inherited_node(AbsoluteNodeLabel(flow_name="flow", node_name="node")) == Node(
        misc={"k1": "g1", "k2": "l1", "k3": "n1", "k4": "n2", "k5": "n3"}
    )
    # assert not changed
    assert script.global_node == global_node
    assert script.get_flow("flow").local_node == local_node
    assert script.get_node(AbsoluteNodeLabel(flow_name="flow", node_name="node")) == node
