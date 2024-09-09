"""
Conditions
----------
The conditions module contains functions that determine whether the pipeline component should be executed or not.

The standard set of them allows user to set up dependencies between pipeline components.
"""

from __future__ import annotations
import asyncio
from typing import Optional

from chatsky.core.context import Context
from chatsky.core.script_function import BaseCondition

from chatsky.core.service.types import (
    ComponentExecutionState,
)

from chatsky.utils.devel.async_helpers import async_infinite_sleep


class ServiceFinishedCondition(BaseCondition):
    """
    Check if a :py:class:`~.chatsky.core.service.Service` was executed successfully.
    """

    path: str
    """The path of the condition pipeline component."""
    wait: bool = False
    """
    Whether the function should wait for the service to be finished.
    By default, the service is not awaited.
    """

    def __init__(self, path, wait=False):
        super().__init__(path=path, wait=wait)

    # This still needs one field in the Context() object, but I think this is required.
    async def call(self, ctx: Context) -> bool:
        if self.wait:
            service_finished = ctx.framework_data.service_finished.get(self.path, None)
            if service_finished is None:
                service_finished = asyncio.Event()
                ctx.framework_data.service_finished[self.path] = service_finished
            await service_finished.wait()

        state = ctx.framework_data.service_states.get(self.path, ComponentExecutionState.NOT_RUN)

        return ComponentExecutionState[state] == ComponentExecutionState.FINISHED
