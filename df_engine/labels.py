"""
Labels
---------------------------
:py:const:`Labels <df_engine.core.types.NodeLabel3Type>` are one of
the most important components of the dialog graph,
which determine targeted node name of transition.
This is a standard set of engine
:py:const:`labels <df_engine.core.types.NodeLabelType>`.

"""
from typing import Optional, Callable
from .core.actor import Actor
from .core.context import Context
from .core.types import NodeLabel3Type


def repeat(priority: Optional[float] = None, *args, **kwargs) -> Callable:
    """
    Returns transition handler that takes :py:class:`~df_engine.core.context.Context`,
    :py:class:`~df_engine.core.actor.Actor` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <df_engine.core.types.NodeLabelType>`
    to the last node with a given  :py:const:`priority <float>`.
    If the priority is not given, `Actor.label_priority` is used as default.

    Parameters
    -----------

    priority: Optional[float] = None
        float priority of transition. Uses `Actor.label_priority` if priority not defined.
    """

    def repeat_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        current_priority = actor.label_priority if priority is None else priority
        if len(ctx.labels) >= 1:
            flow_label, label = list(ctx.labels.values())[-1]
        else:
            flow_label, label = actor.fallback_label[:2]
        return (flow_label, label, current_priority)

    return repeat_transition_handler


def previous(priority: Optional[float] = None, *args, **kwargs) -> Callable:
    """
    Returns transition handler that takes :py:class:`~df_engine.core.context.Context`,
    :py:class:`~df_engine.core.actor.Actor` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <df_engine.core.types.NodeLabelType>`
    to the previous node with a given :py:const:`priority <float>`.
    If the priority is not given, `Actor.label_priority` is used as default.

    Parameters
    -----------

    priority: Optional[float] = None
        float priority of transition. Uses `Actor.label_priority` if priority not defined.
    """

    def previous_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        current_priority = actor.label_priority if priority is None else priority
        if len(ctx.labels) >= 2:
            flow_label, label = list(ctx.labels.values())[-2]
        else:
            flow_label, label = actor.fallback_label[:2]
        return (flow_label, label, current_priority)

    return previous_transition_handler


def to_start(priority: Optional[float] = None, *args, **kwargs) -> Callable:
    """
    Returns transition handler that takes :py:class:`~df_engine.core.context.Context`,
    :py:class:`~df_engine.core.actor.Actor` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <df_engine.core.types.NodeLabelType>`
    to the start node with a given :py:const:`priority <float>`.
    If the priority is not given, `Actor.label_priority` is used as default.

    Parameters
    -----------

    priority: Optional[float] = None
        float priority of transition. Uses `Actor.label_priority` if :py:const:`priority <float>` not defined.
    """

    def to_start_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        current_priority = actor.label_priority if priority is None else priority
        return (*actor.start_label[:2], current_priority)

    return to_start_transition_handler


def to_fallback(priority: Optional[float] = None, *args, **kwargs) -> Callable:
    """
    Returns transition handler that takes :py:class:`~df_engine.core.context.Context`,
    :py:class:`~df_engine.core.actor.Actor` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <df_engine.core.types.NodeLabelType>`
    to the fallback node with a given :py:const:`priority <float>`.
    If the priority is not given, `Actor.label_priority` is used as default.

    Parameters
    -----------

    priority: Optional[float] = None
        float priority of transition. Uses `Actor.label_priority` if :py:const:`priority <float>` not defined.
    """

    def to_fallback_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        current_priority = actor.label_priority if priority is None else priority
        return (*actor.fallback_label[:2], current_priority)

    return to_fallback_transition_handler


def _get_label_by_index_shifting(
    ctx: Context,
    actor: Actor,
    priority: Optional[float] = None,
    increment_flag: bool = True,
    cyclicality_flag: bool = True,
    *args,
    **kwargs,
) -> NodeLabel3Type:
    """
    Function that returns node label from the context and actor after shifting the index.

    Parameters
    ----------

    ctx: :py:class:`~df_engine.core.context.Context`
        dialog context
    actor: :py:class:`~df_engine.core.actor.Actor`
        dialog actor
    priority: Optional[float] = None
        priority of transition. Used actor.label_priority if not set.
    increment_flag: if it is True, label index is incremented by 1,otherwise it is decreased by 1
    cyclicality_flag: if it is True, the iteration over the label list is going cyclically
    (e.g the element with index=len(labels) has index=0)

    Returned values: the tuple that consists of (flow_label, label, priority).
    If fallback is executed, (flow_fallback_label, fallback_label, priority) are returned.


    """
    flow_label, node_label, current_priority = repeat(priority, *args, **kwargs)(ctx, actor, *args, **kwargs)
    labels = list(actor.script.get(flow_label, {}))

    if node_label not in labels:
        return (*actor.fallback_label[:2], current_priority)

    label_index = labels.index(node_label)
    label_index = label_index + 1 if increment_flag else label_index - 1
    if not (cyclicality_flag or (0 <= label_index < len(labels))):
        return (*actor.fallback_label[:2], current_priority)
    label_index %= len(labels)

    return (flow_label, labels[label_index], current_priority)


def forward(priority: Optional[float] = None, cyclicality_flag: bool = True, *args, **kwargs) -> Callable:
    """
    Returns transition handler that takes :py:class:`~df_engine.core.context.Context`,
    :py:class:`~df_engine.core.actor.Actor` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <df_engine.core.types.NodeLabelType>`
    to the forward node with a given :py:const:`priority <float>`
    and :py:const:`cyclicality_flag <bool>`.
    If the priority is not given, `Actor.label_priority` is used as default.

    Parameters
    ----------

    priority: Optional[float] = None
        float priority of transition. Used `Actor.label_priority` if not defined.
    """

    def forward_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        return _get_label_by_index_shifting(
            ctx, actor, priority, increment_flag=True, cyclicality_flag=cyclicality_flag
        )

    return forward_transition_handler


def backward(priority: Optional[float] = None, cyclicality_flag: bool = True, *args, **kwargs) -> Callable:
    """
    Returns transition handler that takes :py:class:`~df_engine.core.context.Context`,
    :py:class:`~df_engine.core.actor.Actor` and :py:const:`priority <float>`.
    This handler returns a :py:const:`label <df_engine.core.types.NodeLabelType>`
    to the backward node with a given :py:const:`priority <float>`
    and :py:const:`cyclicality_flag <bool>`.
    If the priority is not given, `Actor.label_priority` is used as default.

    Parameters
    ----------

    priority: Optional[float] = None
        float priority of transition. Uses `Actor.label_priority` if priority not defined.
    """

    def back_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        return _get_label_by_index_shifting(
            ctx, actor, priority, increment_flag=False, cyclicality_flag=cyclicality_flag
        )

    return back_transition_handler
