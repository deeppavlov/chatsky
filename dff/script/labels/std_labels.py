"""
Labels
------
:py:const:`Labels <dff.script.NodeLabel3Type>` are one of the important components of the dialog graph,
which determine the targeted node name of the transition.
They are used to identify the next step in the conversation.
Labels can also be used in combination with other conditions,
such as the current context or user data, to create more complex and dynamic conversations.

This module contains a standard set of scripting :py:const:`labels <dff.script.NodeLabelType>` that
can be used by developers to define the conversation flow.
"""
from typing import Optional, Callable, ForwardRef
from dff.script import Context, NodeLabel3Type

Pipeline = ForwardRef("Pipeline")


def repeat(priority: Optional[float] = None) -> Callable:
    """
    Returns transition handler that takes :py:class:`.Context`,
    :py:class:`~dff.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <NodeLabelType>`
    to the last node with a given :py:const:`priority <float>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.

    :param priority: Priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    """

    def repeat_transition_handler(ctx: Context, pipeline: Pipeline, *args, **kwargs) -> NodeLabel3Type:
        current_priority = pipeline.actor.label_priority if priority is None else priority
        if len(ctx.labels) >= 1:
            flow_label, label = list(ctx.labels.values())[-1]
        else:
            flow_label, label = pipeline.actor.start_label[:2]
        return (flow_label, label, current_priority)

    return repeat_transition_handler


def previous(priority: Optional[float] = None) -> Callable:
    """
    Returns transition handler that takes :py:class:`~dff.script.Context`,
    :py:class:`~dff.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <dff.script.NodeLabelType>`
    to the previous node with a given :py:const:`priority <float>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.
    If the current node is the start node, fallback is returned.

    :param priority: Priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    """

    def previous_transition_handler(ctx: Context, pipeline: Pipeline, *args, **kwargs) -> NodeLabel3Type:
        current_priority = pipeline.actor.label_priority if priority is None else priority
        if len(ctx.labels) >= 2:
            flow_label, label = list(ctx.labels.values())[-2]
        elif len(ctx.labels) == 1:
            flow_label, label = pipeline.actor.start_label[:2]
        else:
            flow_label, label = pipeline.actor.fallback_label[:2]
        return (flow_label, label, current_priority)

    return previous_transition_handler


def to_start(priority: Optional[float] = None) -> Callable:
    """
    Returns transition handler that takes :py:class:`~dff.script.Context`,
    :py:class:`~dff.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <dff.script.NodeLabelType>`
    to the start node with a given :py:const:`priority <float>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.

    :param priority: Priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    """

    def to_start_transition_handler(ctx: Context, pipeline: Pipeline, *args, **kwargs) -> NodeLabel3Type:
        current_priority = pipeline.actor.label_priority if priority is None else priority
        return (*pipeline.actor.start_label[:2], current_priority)

    return to_start_transition_handler


def to_fallback(priority: Optional[float] = None) -> Callable:
    """
    Returns transition handler that takes :py:class:`~dff.script.Context`,
    :py:class:`~dff.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <dff.script.NodeLabelType>`
    to the fallback node with a given :py:const:`priority <float>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.

    :param priority: Priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    """

    def to_fallback_transition_handler(ctx: Context, pipeline: Pipeline, *args, **kwargs) -> NodeLabel3Type:
        current_priority = pipeline.actor.label_priority if priority is None else priority
        return (*pipeline.actor.fallback_label[:2], current_priority)

    return to_fallback_transition_handler


def _get_label_by_index_shifting(
    ctx: Context,
    pipeline: Pipeline,
    priority: Optional[float] = None,
    increment_flag: bool = True,
    cyclicality_flag: bool = True,
    *args,
    **kwargs,
) -> NodeLabel3Type:
    """
    Function that returns node label from the context and pipeline after shifting the index.

    :param ctx: Dialog context.
    :param pipeline: Dialog pipeline.
    :param priority: Priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    :param increment_flag: If it is `True`, label index is incremented by `1`,
        otherwise it is decreased by `1`. Defaults to `True`.
    :param cyclicality_flag: If it is `True` the iteration over the label list is going cyclically
        (e.g the element with `index = len(labels)` has `index = 0`). Defaults to `True`.
    :return: The tuple that consists of `(flow_label, label, priority)`.
        If fallback is executed `(flow_fallback_label, fallback_label, priority)` are returned.
    """
    flow_label, node_label, current_priority = repeat(priority)(ctx, pipeline, *args, **kwargs)
    labels = list(pipeline.script.get(flow_label, {}))

    if node_label not in labels:
        return (*pipeline.actor.fallback_label[:2], current_priority)

    label_index = labels.index(node_label)
    label_index = label_index + 1 if increment_flag else label_index - 1
    if not (cyclicality_flag or (0 <= label_index < len(labels))):
        return (*pipeline.actor.fallback_label[:2], current_priority)
    label_index %= len(labels)

    return (flow_label, labels[label_index], current_priority)


def forward(priority: Optional[float] = None, cyclicality_flag: bool = True) -> Callable:
    """
    Returns transition handler that takes :py:class:`~dff.script.Context`,
    :py:class:`~dff.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <dff.script.NodeLabelType>`
    to the forward node with a given :py:const:`priority <float>` and :py:const:`cyclicality_flag <bool>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.

    :param priority: Float priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    :param cyclicality_flag: If it is `True`, the iteration over the label list is going cyclically
        (e.g the element with `index = len(labels)` has `index = 0`). Defaults to `True`.
    """

    def forward_transition_handler(ctx: Context, pipeline: Pipeline, *args, **kwargs) -> NodeLabel3Type:
        return _get_label_by_index_shifting(
            ctx, pipeline, priority, increment_flag=True, cyclicality_flag=cyclicality_flag, *args, **kwargs
        )

    return forward_transition_handler


def backward(priority: Optional[float] = None, cyclicality_flag: bool = True) -> Callable:
    """
    Returns transition handler that takes :py:class:`~dff.script.Context`,
    :py:class:`~dff.pipeline.Pipeline` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <dff.script.NodeLabelType>`
    to the backward node with a given :py:const:`priority <float>` and :py:const:`cyclicality_flag <bool>`.
    If the priority is not given, `Pipeline.actor.label_priority` is used as default.

    :param priority: Float priority of transition. Uses `Pipeline.actor.label_priority` if priority not defined.
    :param cyclicality_flag: If it is `True`, the iteration over the label list is going cyclically
        (e.g the element with `index = len(labels)` has `index = 0`). Defaults to `True`.
    """

    def back_transition_handler(ctx: Context, pipeline: Pipeline, *args, **kwargs) -> NodeLabel3Type:
        return _get_label_by_index_shifting(
            ctx, pipeline, priority, increment_flag=False, cyclicality_flag=cyclicality_flag, *args, **kwargs
        )

    return back_transition_handler
