from dff.script.core.types import NodeLabel3Type
from dff.script import Context
from dff.pipeline import Pipeline
import typing as tp


def greeting_flow_n2_transition(
    _: Context, __: Pipeline, *args, **kwargs
) -> NodeLabel3Type:
    return "greeting_flow", "node2", 1.0


def high_priority_node_transition(
    flow_label: str, label: str
) -> tp.Callable[..., NodeLabel3Type]:
    def transition(_: Context, __: Pipeline, *args, **kwargs) -> NodeLabel3Type:
        return flow_label, label, 2.0

    return transition
