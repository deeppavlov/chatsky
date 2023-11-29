"""
Conditions
----------
The conditions module contains functions that can be used to determine whether the pipeline component to which they
are attached should be executed or not.
The standard set of them allows user to setup dependencies between pipeline components.
"""
from typing import Optional, ForwardRef

from dff.script import Context

from .types import (
    PIPELINE_STATE_KEY,
    StartConditionCheckerFunction,
    ComponentExecutionState,
    StartConditionCheckerAggregationFunction,
)

Pipeline = ForwardRef("Pipeline")


def always_start_condition(_: Context, __: Pipeline) -> bool:
    """
    Condition that always allows service execution. It's the default condition for all services.

    :param _: Current dialog context.
    :param __: Pipeline.
    """
    return True


def service_successful_condition(path: Optional[str] = None) -> StartConditionCheckerFunction:
    """
    Condition that allows service execution, only if the other service was executed successfully.
    Returns :py:data:`~.StartConditionCheckerFunction`.

    :param path: The path of the condition pipeline component.
    """

    def check_service_state(ctx: Context, _: Pipeline):
        state = ctx.framework_states[PIPELINE_STATE_KEY].get(path, ComponentExecutionState.NOT_RUN)
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
