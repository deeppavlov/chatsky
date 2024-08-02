import pytest

from chatsky.core.context import get_last_index, Context, ContextError
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.message import Message


@pytest.mark.parametrize("dict,result", [
    ({}, -1),
    ({1: None, 5: None}, 5),
    ({5: None, 1: None}, 5),
])
def test_get_last_index(dict, result):
    assert get_last_index(dict) == result


def test_init():
    ctx1 = Context.init(AbsoluteNodeLabel(flow_name="flow", node_name="node"))
    ctx2 = Context.init(AbsoluteNodeLabel(flow_name="flow", node_name="node"))
    assert ctx1.labels == {-1: AbsoluteNodeLabel(flow_name="flow", node_name="node")}
    assert ctx1.id != ctx2.id

    ctx3 = Context.init(AbsoluteNodeLabel(flow_name="flow", node_name="node"), id="id")
    assert ctx3.labels == {-1: AbsoluteNodeLabel(flow_name="flow", node_name="node")}
    assert ctx3.id == "id"


def test_labels():
    ctx = Context.model_validate({"labels": {5: ("flow", "node1")}})

    assert ctx.last_label == AbsoluteNodeLabel(flow_name="flow", node_name="node1")
    ctx.add_label(("flow", "node2"))
    assert ctx.labels == {5: AbsoluteNodeLabel(flow_name="flow", node_name="node1"), 6: AbsoluteNodeLabel(flow_name="flow", node_name="node2")}
    assert ctx.last_label == AbsoluteNodeLabel(flow_name="flow", node_name="node2")

    ctx.labels = {}
    with pytest.raises(ContextError):
        ctx.last_label


def test_requests():
    ctx = Context(labels={}, requests={5: "text1"})
    assert ctx.last_request == Message("text1")
    ctx.add_request("text2")
    assert ctx.requests == {5: Message("text1"), 6: Message("text2")}
    assert ctx.last_request == Message("text2")

    ctx.requests = {}
    with pytest.raises(ContextError):
        ctx.last_request


def test_responses():
    ctx = Context(labels={}, responses={5: "text1"})
    assert ctx.last_response == Message("text1")
    ctx.add_response("text2")
    assert ctx.responses == {5: Message("text1"), 6: Message("text2")}
    assert ctx.last_response == Message("text2")

    ctx.responses = {}
    assert ctx.last_response is None
