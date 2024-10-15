"""
Service Conditions
------------------
Provides service-related conditions
"""

from __future__ import annotations

from chatsky.core.context import Context
from chatsky.core.script_function import BaseCondition

from chatsky.core.service.types import (
    ComponentExecutionState,
)


class ServiceFinished(BaseCondition):
    """
    Check if a :py:class:`~chatsky.core.service.service.Service` was executed successfully.
    """

    path: str
    """The path of the condition pipeline component."""
    wait: bool = False
    """
    Whether to wait for the service to be finished.

    This eliminates possible service states ``NOT_RUN`` and ``RUNNING``.
    """

    def __init__(self, path: str, *, wait: bool = False):
        super().__init__(path=path, wait=wait)

    async def call(self, ctx: Context) -> bool:
        if self.wait:
            await ctx.framework_data.service_states[self.path].finished_event.wait()

        state = ctx.framework_data.service_states[self.path].execution_status

        return ComponentExecutionState[state] == ComponentExecutionState.FINISHED
