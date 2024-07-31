"""
Labels
------
:py:const:`Labels <chatsky.script.ConstLabel>` are one of the important components of the dialog graph,
which determine the targeted node name of the transition.
They are used to identify the next step in the conversation.
Labels can also be used in combination with other conditions,
such as the current context or user data, to create more complex and dynamic conversations.

This module contains a standard set of scripting :py:const:`labels <chatsky.script.ConstLabel>` that
can be used by developers to define the conversation flow.
"""

from __future__ import annotations

from pydantic import Field

from chatsky.core.context import get_last_index, Context
from chatsky.core.node_label import NodeLabelInitTypes, AbsoluteNodeLabel
from chatsky.core.script_function import BaseDestination


class Repeat(BaseDestination):
    """
    Returns transition handler that takes :py:class:`.Context`,
    :py:class:`~chatsky.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <ConstLabel>`
    to the last node with a given :py:const:`priority <float>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.

    :param priority: Priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    """

    shift: int = Field(default=0, ge=0)

    async def func(self, ctx: Context) -> NodeLabelInitTypes:
        index = get_last_index(ctx.labels)
        shifted_index = index - self.shift
        result = ctx.labels.get(shifted_index)
        if result is None:
            raise KeyError(f"No label with index {shifted_index!r}. "
                           f"Current label index: {index!r}; Repeat.shift: {self.shift!r}.")
        return result


class Start(BaseDestination):
    """
    Returns transition handler that takes :py:class:`~chatsky.script.Context`,
    :py:class:`~chatsky.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <chatsky.script.ConstLabel>`
    to the start node with a given :py:const:`priority <float>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.

    :param priority: Priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    """

    async def func(self, ctx: Context) -> NodeLabelInitTypes:
        return ctx.pipeline.actor.start_label


class Fallback(BaseDestination):
    """
    Returns transition handler that takes :py:class:`~chatsky.script.Context`,
    :py:class:`~chatsky.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <chatsky.script.ConstLabel>`
    to the fallback node with a given :py:const:`priority <float>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.

    :param priority: Priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    """

    async def func(self, ctx: Context) -> NodeLabelInitTypes:
        return ctx.pipeline.actor.fallback_label


def get_next_node_in_flow(
    node_label: AbsoluteNodeLabel,
    ctx: Context,
    *,
    increment: bool = True,
    loop: bool = False,
) -> AbsoluteNodeLabel:
    """
    Function that returns node label from the context and pipeline after shifting the index.

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
    Returns transition handler that takes :py:class:`~chatsky.script.Context`,
    :py:class:`~chatsky.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <chatsky.script.ConstLabel>`
    to the forward node with a given :py:const:`priority <float>` and :py:const:`cyclicality_flag <bool>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.

    :param priority: Float priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    :param cyclicality_flag: If it is `True`, the iteration over the label list is going cyclically
        (e.g the element with `index = len(labels)` has `index = 0`). Defaults to `True`.
    """
    loop: bool = False

    async def func(self, ctx: Context) -> NodeLabelInitTypes:
        return get_next_node_in_flow(
            ctx.last_label,
            ctx,
            increment=True,
            loop=self.loop
        )


class Backward(BaseDestination):
    """
    Returns transition handler that takes :py:class:`~chatsky.script.Context`,
    :py:class:`~chatsky.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <chatsky.script.ConstLabel>`
    to the backward node with a given :py:const:`priority <float>` and :py:const:`cyclicality_flag <bool>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.

    :param priority: Float priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    :param cyclicality_flag: If it is `True`, the iteration over the label list is going cyclically
        (e.g the element with `index = len(labels)` has `index = 0`). Defaults to `True`.
    """
    loop: bool = False

    async def func(self, ctx: Context) -> NodeLabelInitTypes:
        return get_next_node_in_flow(
            ctx.last_label,
            ctx,
            increment=False,
            loop=self.loop
        )
