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

from chatsky.core.service.types import (
    StartConditionCheckerFunction,
    ComponentExecutionState,
    StartConditionCheckerAggregationFunction,
)

from chatsky.utils.devel.async_helpers import async_infinite_sleep

if TYPE_CHECKING:
    from chatsky.core.pipeline import Pipeline


def always_start_condition(_: Context, __: Pipeline) -> bool:
    """
    Condition that always allows service execution. It's the default condition for all services.

    :param _: Current dialog context.
    :param __: Pipeline.
    """
    return True


def service_successful_condition(path: Optional[str] = None, wait: bool = False) -> StartConditionCheckerFunction:
    """
    Condition that allows service execution, only if the other service was executed successfully.
    Returns :py:data:`~.StartConditionCheckerFunction`.

    :param path: The path of the condition pipeline component.
    :param wait: Whether the function should wait for the service to be finished.
        By default, the service is not awaited.
    :type wait: bool
    """

    def check_service_state(ctx: Context):
        # Just making sure that 'path' was given (or it would break the code.)
        if wait and path:
            # Placeholder task solution (needs review)
            # The point is, the task gets cancelled by PipelineComponent.__call__(self, ctx)
            # I feel like this is fairly efficient, but most importantly,
            # there won't be any delays to the code. 'wait' is just True or False now.

            # There's just one problem, I'm heavily using 'framework_data' from Context,
            # and now it's kinda dirty. I could maybe make a class ServiceData or something
            # so that 'framework_data' is more concise.

            # Also, if the 'path' is wrong, this will go into an infinite cycle.
            # Could make a maximum waiting time, though. And add a logger message.
            # Or just check if a path is taken somehow.
            service_started_task = ctx.framework_data.service_started_flag_tasks.get(path, None)
            if not service_started_task:
                service_started_task = asyncio.create_task(async_infinite_sleep())
                ctx.framework_data.service_started_flag_tasks[path] = service_started_task

            try:
                await service_started_task
            except asyncio.CancelledError:
                pass

            service_task = ctx.framework_data.service_asyncio_tasks.get(path, None)
            await service_task

        state = ctx.framework_data.service_states.get(path, ComponentExecutionState.NOT_RUN)

        return ComponentExecutionState[state] == ComponentExecutionState.FINISHED

    return check_service_state


def not_condition(func: StartConditionCheckerFunction) -> StartConditionCheckerFunction:
    """
    Condition that returns opposite boolean value to the one returned by incoming function.
    Returns :py:data:`~.StartConditionCheckerFunction`.

    :param func: The function to return opposite of.
    """

    def not_function(ctx: Context, pipeline: Pipeline):
        return not func(ctx, pipeline)

    return not_function


def aggregate_condition(
    aggregator: StartConditionCheckerAggregationFunction, *functions: StartConditionCheckerFunction
) -> StartConditionCheckerFunction:
    """
    Condition that returns aggregated boolean value from all booleans returned by incoming functions.
    Returns :py:data:`~.StartConditionCheckerFunction`.

    :param aggregator: The function that accepts list of booleans and returns a single boolean.
    :param functions: Functions to aggregate.
    """

    def aggregation_function(ctx: Context, pipeline: Pipeline):
        return aggregator([func(ctx, pipeline) for func in functions])

    return aggregation_function


def all_condition(*functions: StartConditionCheckerFunction) -> StartConditionCheckerFunction:
    """
    Condition that returns `True` only if all incoming functions return `True`.
    Returns :py:data:`~.StartConditionCheckerFunction`.

    :param functions: Functions to aggregate.
    """
    return aggregate_condition(all, *functions)


def any_condition(*functions: StartConditionCheckerFunction) -> StartConditionCheckerFunction:
    """
    Condition that returns `True` if any of incoming functions returns `True`.
    Returns :py:data:`~.StartConditionCheckerFunction`.

    :param functions: Functions to aggregate.
    """
    return aggregate_condition(any, *functions)
