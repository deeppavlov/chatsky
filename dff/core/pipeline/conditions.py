from typing import Optional

from dff.core.engine.core import Actor, Context

from .types import (
    PIPELINE_STATE_KEY,
    StartConditionCheckerFunction,
    ComponentExecutionState,
    StartConditionCheckerAggregationFunction,
)


def always_start_condition(_: Context, __: Actor) -> bool:
    """
    Condition that always allows service execution, it's the default condition for all services.
    Returns bool (True).

    :param ctx: current dialog context.
    :type ctx: Context
    :param actor: pipeline actor.
    :type actor: Actor
    """
    return True


def service_successful_condition(path: Optional[str] = None) -> StartConditionCheckerFunction:
    """
    Condition that allows service execution, only if the other service was executed successfully.
    Returns StartConditionCheckerFunction.

    :param path: the path of the condition pipeline component.
    :type path: Optional[str]
    """

    def check_service_state(ctx: Context, _: Actor):
        state = ctx.framework_states[PIPELINE_STATE_KEY].get(path, ComponentExecutionState.NOT_RUN.name)
        return ComponentExecutionState[state] == ComponentExecutionState.FINISHED

    return check_service_state


def not_condition(function: StartConditionCheckerFunction) -> StartConditionCheckerFunction:
    """
    Condition that returns opposite boolean value to the one returned by incoming function.
    Returns StartConditionCheckerFunction.

    :param function: the function to return opposite of.
    :type function: StartConditionCheckerFunction
    """

    def not_function(ctx: Context, actor: Actor):
        return not function(ctx, actor)

    return not_function


def aggregate_condition(
    aggregator: StartConditionCheckerAggregationFunction, *functions: StartConditionCheckerFunction
) -> StartConditionCheckerFunction:
    """
    Condition that returns aggregated boolean value from all booleans returned by incoming functions.
    Returns StartConditionCheckerFunction.

    :param aggregator:
        the function that accepts list of booleans and returns a single boolean.
    :type aggregator: StartConditionCheckerAggregationFunction
    :param functions: functions to aggregate.
    :type functions: StartConditionCheckerFunction
    """

    def aggregation_function(ctx: Context, actor: Actor):
        return aggregator([function(ctx, actor) for function in functions])

    return aggregation_function


def all_condition(*functions: StartConditionCheckerFunction) -> StartConditionCheckerFunction:
    """
    Condition that returns True only if all incoming functions return True.
    Returns StartConditionCheckerFunction.

    :param functions: functions to aggregate.
    :type functions: StartConditionCheckerFunction
    """
    return aggregate_condition(all, *functions)


def any_condition(*functions: StartConditionCheckerFunction) -> StartConditionCheckerFunction:
    """
    Condition that returns True if any of incoming functions returns True.
    Returns StartConditionCheckerFunction.

    :param functions: functions to aggregate.
    :type functions: StartConditionCheckerFunction
    """
    return aggregate_condition(any, *functions)
