"""
Conditions
----------
"""
from typing import Optional

from dff.script import Actor, Context

from .types import (
    PIPELINE_STATE_KEY,
    StartConditionCheckerFunction,
    ComponentExecutionState,
    StartConditionCheckerAggregationFunction,
)


def always_start_condition(_: Context, __: Actor) -> bool:
    """
    Condition that always allows service execution. It's the default condition for all services.

    :param ctx: Current dialog context.
    :param actor: Pipeline actor.
    """
    return True


def service_successful_condition(path: Optional[str] = None) -> StartConditionCheckerFunction:
    """
    Condition that allows service execution, only if the other service was executed successfully.
    Returns :py:data:`~.StartConditionCheckerFunction`.

    :param path: The path of the condition pipeline component.
    """

    def check_service_state(ctx: Context, _: Actor):
        state = ctx.framework_states[PIPELINE_STATE_KEY].get(path, ComponentExecutionState.NOT_RUN.name)
        return ComponentExecutionState[state] == ComponentExecutionState.FINISHED

    return check_service_state


def not_condition(function: StartConditionCheckerFunction) -> StartConditionCheckerFunction:
    """
    Condition that returns opposite boolean value to the one returned by incoming function.
    Returns :py:data:`~.StartConditionCheckerFunction`.

    :param function: The function to return opposite of.
    """

    def not_function(ctx: Context, actor: Actor):
        return not function(ctx, actor)

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

    def aggregation_function(ctx: Context, actor: Actor):
        return aggregator([function(ctx, actor) for function in functions])

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
