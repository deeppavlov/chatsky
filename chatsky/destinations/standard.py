"""
Standard Destinations
---------------------
This module provides basic destinations.

- :py:class:`Repeat` -- history-based destination;
- :py:class:`Start` and :py:class:`Fallback` -- config-based destinations;
- :py:class:`Forward` and :py:class:`Backward` -- script-based destinations.
"""

from __future__ import annotations

from pydantic import Field

from chatsky.core.context import get_last_index, Context
from chatsky.core.node_label import NodeLabelInitTypes, AbsoluteNodeLabel
from chatsky.core.script_function import BaseDestination


class Repeat(BaseDestination):
    """
    Return label of the node located at a certain position in the label history.

    Return label of the last visited node by default.
    """

    shift: int = Field(default=0, ge=0)
    """
    Position of the node in the history from the last element.
    
    Shift 0 means last label; shift 1 means second to last label; e.t.c.
    """

    async def call(self, ctx: Context) -> NodeLabelInitTypes:
        index = get_last_index(ctx.labels)
        shifted_index = index - self.shift
        result = ctx.labels.get(shifted_index)
        if result is None:
            raise KeyError(f"No label with index {shifted_index!r}. "
                           f"Current label index: {index!r}; Repeat.shift: {self.shift!r}.")
        return result


class Start(BaseDestination):
    """
    Return :py:attr:`~chatsky.core.pipeline.Pipeline.start_label`.
    """

    async def call(self, ctx: Context) -> NodeLabelInitTypes:
        return ctx.pipeline.start_label


class Fallback(BaseDestination):
    """
    Return :py:attr:`~chatsky.core.pipeline.Pipeline.fallback_label`.
    """

    async def call(self, ctx: Context) -> NodeLabelInitTypes:
        return ctx.pipeline.fallback_label


def get_next_node_in_flow(
    node_label: AbsoluteNodeLabel,
    ctx: Context,
    *,
    increment: bool = True,
    loop: bool = False,
) -> AbsoluteNodeLabel:
    """
    Function that returns node label of a node in the same flow after shifting the index.

    :param node_label: Label of the node to shift from.
    :param ctx: Dialog context.
    :param increment: If it is `True`, label index is incremented by `1`,
        otherwise it is decreased by `1`.
    :param loop: If it is `True` the iteration over the label list is going cyclically
        (i.e. Backward in the first node returns the last node).
    :return: The tuple that consists of `(flow_label, label, priority)`.
        If fallback is executed `(flow_fallback_label, fallback_label, priority)` are returned.
    """
    node_label = AbsoluteNodeLabel.model_validate(node_label, context={"ctx": ctx})
    node_keys = list(ctx.pipeline.script.get_flow(node_label.flow_name).nodes.keys())

    node_index = node_keys.index(node_label.node_name)
    node_index = node_index + 1 if increment else node_index - 1
    if not (loop or (0 <= node_index < len(node_keys))):
        raise IndexError(f"Node index {node_index!r} out of range for node_keys: {node_keys!r}."
                         f"Consider using the `loop` flag.")
    node_index %= len(node_keys)

    return AbsoluteNodeLabel(flow_name=node_label.flow_name, node_name=node_keys[node_index])


class Forward(BaseDestination):
    """
    Return the next node relative to the current node in the current flow.
    """
    loop: bool = False
    """
    Whether to return the first node of the flow if the current node is the last one.
    Otherwise and exception is raised (and transition is considered unsuccessful).
    """

    async def call(self, ctx: Context) -> NodeLabelInitTypes:
        return get_next_node_in_flow(
            ctx.last_label,
            ctx,
            increment=True,
            loop=self.loop
        )


class Backward(BaseDestination):
    """
    Return the previous node relative to the current node in the current flow.
    """
    loop: bool = False
    """
    Whether to return the last node of the flow if the current node is the first one.
    Otherwise and exception is raised (and transition is considered unsuccessful).
    """

    async def call(self, ctx: Context) -> NodeLabelInitTypes:
        return get_next_node_in_flow(
            ctx.last_label,
            ctx,
            increment=False,
            loop=self.loop
        )
