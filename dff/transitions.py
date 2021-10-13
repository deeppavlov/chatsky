from typing import Optional
from .core.actor import Actor
from .core.context import Context


def repeat(priority: Optional[float] = None, *args, **kwargs):
    def repeat_transition(ctx: Context, actor: Actor, *args, **kwargs) -> tuple[str, str, float]:
        turn_index = ctx.previous_index
        flow_label, label = ctx.labels.get(turn_index, actor.fallback_label[:2])
        current_priority = actor.default_transition_priority if priority is None else priority
        return (flow_label, label, current_priority)

    return repeat_transition


def previous(priority: Optional[float] = None, *args, **kwargs):
    def previous_transition(ctx: Context, actor: Actor, *args, **kwargs) -> tuple[str, str, float]:
        turn_index = ctx.previous_index - 1
        flow_label, label = ctx.labels.get(turn_index, actor.fallback_label[:2])
        current_priority = actor.default_transition_priority if priority is None else priority
        return (flow_label, label, current_priority)

    return previous_transition


def to_start(priority: Optional[float] = None, *args, **kwargs):
    def to_start_transition(ctx: Context, actor: Actor, *args, **kwargs) -> tuple[str, str, float]:
        current_priority = actor.default_transition_priority if priority is None else priority
        return (*actor.start_label[:2], current_priority)

    return to_start_transition


def to_fallback(priority: Optional[float] = None, *args, **kwargs):
    def to_fallback_transition(ctx: Context, actor: Actor, *args, **kwargs) -> tuple[str, str, float]:
        current_priority = actor.default_transition_priority if priority is None else priority
        return (*actor.fallback_label[:2], current_priority)

    return to_fallback_transition


def _get_label_by_index_shifting(
    ctx: Context,
    actor: Actor,
    priority: Optional[float] = None,
    increment_flag: bool = True,
    *args,
    **kwargs,
):
    turn_index = ctx.previous_index
    tgt_flow_label, label = ctx.labels.get(turn_index, actor.fallback_label[:2])
    plot = actor.plot
    flow = plot[tgt_flow_label]
    labels = list(flow.graph)
    current_priority = actor.default_transition_priority if priority is None else priority

    if label not in labels:
        return (*actor.fallback_label[:2], current_priority)

    label_index = labels.index(label)
    tgt_label_index = label_index + 1 if increment_flag else label_index - 1
    if not (0 <= tgt_label_index < len(labels)):
        return (*actor.fallback_label[:2], current_priority)

    tgt_label = labels[tgt_label_index]
    return (tgt_flow_label, tgt_label, current_priority)


def forward(priority: Optional[float] = None, *args, **kwargs):
    def forward_transition(ctx: Context, actor: Actor, *args, **kwargs) -> tuple[str, str, float]:
        return _get_label_by_index_shifting(ctx, actor, priority, increment_flag=True)

    return forward_transition


def backward(priority: Optional[float] = None, *args, **kwargs):
    def back_transition(ctx: Context, actor: Actor, *args, **kwargs) -> tuple[str, str, float]:
        return _get_label_by_index_shifting(ctx, actor, priority, increment_flag=False)

    return back_transition
