"""
Conditions
----------
The conditions module contains functions that determine whether the pipeline component should be executed or not.

The standard set of them allows user to set up dependencies between pipeline components.
"""

from __future__ import annotations
import asyncio
from typing import Optional, TYPE_CHECKING

from chatsky.core.context import Context
from chatsky.core.script_function import BaseCondition

from chatsky.core.service.types import (
    ComponentExecutionState,
    StartConditionCheckerAggregationFunction,
)

from chatsky.utils.devel.async_helpers import async_infinite_sleep

if TYPE_CHECKING:
    from chatsky.core.pipeline import Pipeline


class ServiceFinishedCondition(BaseCondition):
    """
    Check if a :py:class:`~.chatsky.core.service.Service` was executed successfully.
    """
    path: Optional[str] = None
    """The path of the condition pipeline component."""
    wait: bool = False
    """
    Whether the function should wait for the service to be finished.
    By default, the service is not awaited.
    """

    def __init__(self, path, wait = False):
        super().__init__(path=path, wait=wait)

    # Placeholder task solution for efficient awaiting(needs review)
    # The point is, the task gets cancelled by PipelineComponent.__call__(self, ctx)
    # I feel like this is fairly efficient, but most importantly,
    # there won't be any delays to the code. 'wait' is just True or False now, not an 'int'.
    async def call(self, ctx: Context) -> bool:
        # Just making sure that 'path' was given (or it would break the code.)
        if wait and path:
            service_started_task = ctx.framework_data.service_started_flag_tasks.get(path, None)
            if not service_started_task:
                service_started_task = asyncio.create_task(async_infinite_sleep())
                ctx.framework_data.service_started_flag_tasks[path] = service_started_task

            try:
                await
                service_started_task
            except asyncio.CancelledError:
                pass

            service_task = ctx.framework_data.service_asyncio_tasks.get(path, None)
            await
            service_task
        state = ctx.framework_data.service_states.get(path, ComponentExecutionState.NOT_RUN)

        return ComponentExecutionState[state] == ComponentExecutionState.FINISHED

    # There's just one problem, I'm heavily using 'framework_data' from Context,
    # and now it's kinda dirty. I could maybe make a class ServiceData or something
    # so that 'framework_data' is more concise.

    # Also, if the 'path' is wrong, this will go into an infinite cycle.
    # Could make a maximum waiting time, though. And add a logger message.
    # Or just check if a path is taken somehow.
