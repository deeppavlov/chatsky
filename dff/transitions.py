from typing import Optional, Callable
from .core.actor import Actor
from .core.context import Context
from .core.types import NodeLabel3Type


def repeat(priority: Optional[float] = None, *args, **kwargs) -> Callable:
    def repeat_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        current_priority = actor.transition_priority if priority is None else priority
        if len(ctx.labels) >= 1:
            flow_label, label = list(ctx.labels.values())[-1]
        else:
            flow_label, label = actor.fallback_label[:2]
        return (flow_label, label, current_priority)

    return repeat_transition_handler


def previous(priority: Optional[float] = None, *args, **kwargs) -> Callable:
    def previous_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        current_priority = actor.transition_priority if priority is None else priority
        if len(ctx.labels) >= 2:
            flow_label, label = list(ctx.labels.values())[-2]
        else:
            flow_label, label = actor.fallback_label[:2]
        return (flow_label, label, current_priority)

    return previous_transition_handler


def to_start(priority: Optional[float] = None, *args, **kwargs) -> Callable:
    def to_start_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        current_priority = actor.transition_priority if priority is None else priority
        return (*actor.start_label[:2], current_priority)

    return to_start_transition_handler


def to_fallback(priority: Optional[float] = None, *args, **kwargs) -> Callable:
    def to_fallback_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        current_priority = actor.transition_priority if priority is None else priority
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
    flow_label, node_label, current_priority = repeat(priority, *args, **kwargs)(ctx, actor, *args, **kwargs)
    labels = list(actor.plot.get(flow_label, {}))

    if node_label not in labels:
        return (*actor.fallback_label[:2], current_priority)

    label_index = labels.index(node_label)
    label_index = label_index + 1 if increment_flag else label_index - 1
    if not (cyclicality_flag or (0 <= label_index < len(labels))):
        return (*actor.fallback_label[:2], current_priority)
    label_index %= len(labels)

    return (flow_label, labels[label_index], current_priority)


def forward(priority: Optional[float] = None, cyclicality_flag: bool = True, *args, **kwargs) -> Callable:
    def forward_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        return _get_label_by_index_shifting(
            ctx,
            actor,
            priority,
            increment_flag=True,
            cyclicality_flag=cyclicality_flag,
        )

    return forward_transition_handler


def backward(priority: Optional[float] = None, cyclicality_flag: bool = True, *args, **kwargs) -> Callable:
    def back_transition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        return _get_label_by_index_shifting(
            ctx,
            actor,
            priority,
            increment_flag=False,
            cyclicality_flag=cyclicality_flag,
        )

    return back_transition_handler
