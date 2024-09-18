import pytest

from chatsky.core import Transition as Tr, BaseProcessing, Context, AbsoluteNodeLabel
from chatsky.core.script import Node, Flow, Script


class MyProcessing(BaseProcessing):
    value: str = ""

    async def call(self, ctx: Context) -> None:
        return


class TestNodeMerge:
    @pytest.mark.parametrize(
        "first,second,result",
        [
            (
                Node(transitions=[Tr(dst="node3"), Tr(dst="node4")]),
                Node(transitions=[Tr(dst="node1"), Tr(dst="node2")]),
                Node(transitions=[Tr(dst="node3"), Tr(dst="node4"), Tr(dst="node1"), Tr(dst="node2")]),
            ),
            (
                Node(response="msg2"),
                Node(response="msg1"),
                Node(response="msg2"),
            ),
            (
                Node(),
                Node(response="msg1"),
                Node(response="msg1"),
            ),
            (
                Node(pre_response={"key": MyProcessing(value="2")}, pre_transition={}, misc={"k2": "v2"}),
                Node(
                    pre_response={"key": MyProcessing(value="1")},
                    pre_transition={"key": MyProcessing(value="3")},
                    misc={"k1": "v1"},
                ),
                Node(
                    pre_response={"key": MyProcessing(value="2")},
                    pre_transition={"key": MyProcessing(value="3")},
                    misc={"k1": "v1", "k2": "v2"},
                ),
            ),
        ],
    )
    def test_node_merge(self, first, second, result):
        assert first.inherit_from_other(second) == result

    def test_dict_key_order(self):
        global_node_dict = {"1": MyProcessing(value="1"), "3": MyProcessing(value="3")}
        global_node = Node(pre_response=global_node_dict, pre_transition=global_node_dict, misc=global_node_dict)
        local_node_dict = {"1": MyProcessing(value="1*"), "2": MyProcessing(value="2")}
        local_node = Node(pre_response=local_node_dict, pre_transition=local_node_dict, misc=local_node_dict)

        result_node = local_node.model_copy().inherit_from_other(global_node)

        assert list(result_node.pre_response.keys()) == ["1", "2", "3"]
        assert list(result_node.pre_transition.keys()) == ["1", "2", "3"]
        assert list(result_node.misc.keys()) == ["1", "2", "3"]


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
    global_node = Node(misc={"k1": "g1", "k2": "g2", "k3": "g3"})
    local_node = Node(misc={"k2": "l1", "k3": "l2", "k4": "l3"})
    node = Node(misc={"k3": "n1", "k4": "n2", "k5": "n3"})
    global_node_copy = global_node.model_copy(deep=True)
    local_node_copy = local_node.model_copy(deep=True)
    node_copy = node.model_copy(deep=True)

    script = Script.model_validate({"global": global_node, "flow": {"local": local_node, "node": node}})

    assert script.get_inherited_node(AbsoluteNodeLabel(flow_name="", node_name="")) is None
    assert script.get_inherited_node(AbsoluteNodeLabel(flow_name="flow", node_name="")) is None
    inherited_node = script.get_inherited_node(AbsoluteNodeLabel(flow_name="flow", node_name="node"))
    assert inherited_node == Node(misc={"k1": "g1", "k2": "l1", "k3": "n1", "k4": "n2", "k5": "n3"})
    assert list(inherited_node.misc.keys()) == ["k3", "k4", "k5", "k2", "k1"]
    # assert not changed
    assert script.global_node == global_node_copy
    assert script.get_flow("flow").local_node == local_node_copy
    assert script.get_node(AbsoluteNodeLabel(flow_name="flow", node_name="node")) == node_copy
