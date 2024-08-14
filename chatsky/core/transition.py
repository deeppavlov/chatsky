from __future__ import annotations

from typing import Union, List, TYPE_CHECKING, Optional
import logging
import asyncio

from pydantic import BaseModel, Field

from chatsky.core.script_function import AnyCondition, AnyDestination, AnyPriority
from chatsky.core.script_function import BaseCondition, BaseDestination, BasePriority
from chatsky.core.node_label import AbsoluteNodeLabel, NodeLabelInitTypes

if TYPE_CHECKING:
    from chatsky.core.context import Context


logger = logging.getLogger(__name__)


class Transition(BaseModel):
    cnd: AnyCondition = Field(default=True, validate_default=True)
    dst: AnyDestination
    priority: AnyPriority = Field(default=None, validate_default=True)

    def __init__(self, *,
                 cnd: Union[bool, BaseCondition] = True,
                 dst: Union[NodeLabelInitTypes, BaseDestination],
                 priority: Union[Optional[float], BasePriority] = None
                 ):
        super().__init__(cnd=cnd, dst=dst, priority=priority)


async def get_next_label(ctx: Context, transitions: List[Transition], default_priority: float) -> Optional[AbsoluteNodeLabel]:
    filtered_transitions = transitions.copy()
    condition_results = await asyncio.gather(*[transition.cnd(ctx) for transition in filtered_transitions])

    filtered_transitions = [
        transition
        for transition, condition in zip(filtered_transitions, condition_results)
        if condition is True
    ]

    priority_results = await asyncio.gather(*[transition.priority(ctx) for transition in filtered_transitions])

    transitions_with_priorities = [
        (transition, (priority_result if isinstance(priority_result, float) else default_priority))
        for transition, priority_result in zip(filtered_transitions, priority_results)
        if priority_result is True or priority_result is None or isinstance(priority_result, float)
    ]
    logger.debug(f"Possible transitions: {transitions_with_priorities!r}")

    transitions_with_priorities = sorted(transitions_with_priorities, key=lambda x: x[1], reverse=True)

    destination_results = await asyncio.gather(*[transition.dst(ctx) for transition, _ in transitions_with_priorities])

    for destination in destination_results:
        if isinstance(destination, AbsoluteNodeLabel):
            return destination
    return None
