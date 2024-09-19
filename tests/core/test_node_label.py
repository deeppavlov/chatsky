import pytest
from pydantic import ValidationError

from chatsky.core import NodeLabel, Context, AbsoluteNodeLabel, Pipeline


def test_init_from_single_string():
    ctx = Context()
    ctx.framework_data.pipeline = Pipeline({"flow": {"node2": {}}}, ("flow", "node2"))

    node = AbsoluteNodeLabel.model_validate("node2", context={"ctx": ctx})

    assert node == AbsoluteNodeLabel(flow_name="flow", node_name="node2")


@pytest.mark.parametrize("data", [("flow", "node"), ["flow", "node"]])
def test_init_from_iterable(data):
    node = AbsoluteNodeLabel.model_validate(data)
    assert node == AbsoluteNodeLabel(flow_name="flow", node_name="node")


@pytest.mark.parametrize(
    "data,msg",
    [
        (["flow", "node", 3], "list should contain 2 strings"),
        ((1, 2), "tuple should contain 2 strings"),
    ],
)
def test_init_from_incorrect_iterables(data, msg):
    with pytest.raises(ValidationError, match=msg):
        AbsoluteNodeLabel.model_validate(data)


def test_init_from_node_label():
    with pytest.raises(ValidationError):
        AbsoluteNodeLabel.model_validate(NodeLabel(node_name="node"))

    ctx = Context()
    ctx.framework_data.pipeline = Pipeline({"flow": {"node2": {}}}, ("flow", "node2"))

    node = AbsoluteNodeLabel.model_validate(NodeLabel(node_name="node2"), context={"ctx": ctx})

    assert node == AbsoluteNodeLabel(flow_name="flow", node_name="node2")


def test_check_node_exists():
    ctx = Context()
    ctx.framework_data.pipeline = Pipeline({"flow": {"node2": {}}}, ("flow", "node2"))

    with pytest.raises(ValidationError, match="Cannot find node"):
        AbsoluteNodeLabel.model_validate(("flow", "node3"), context={"ctx": ctx})
