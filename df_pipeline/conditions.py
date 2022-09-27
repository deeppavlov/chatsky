from typing import Optional

from df_engine.core import Actor, Context

from .types import (
    PIPELINE_STATE_KEY,
    StartConditionCheckerFunction,
    ComponentExecutionState,
    StartConditionCheckerAggregationFunction,
)


def always_start_condition(_: Context, __: Actor) -> bool:
    """
    Condition that always allows service execution, it's the default condition for all services.
    :ctx: - current dialog context.
    :actor: - pipeline actor.
    Returns bool (True).
    """
    return True


def service_successful_condition(path: Optional[str] = None) -> StartConditionCheckerFunction:
    """
    Condition that allows service execution, only if the other service was executed successfully.
    :path: - the path of the condition pipeline component.
    Returns StartConditionCheckerFunction.
    """

    def check_service_state(ctx: Context, _: Actor):
        state = ctx.framework_states[PIPELINE_STATE_KEY].get(path, ComponentExecutionState.NOT_RUN.name)
        return ComponentExecutionState[state] == ComponentExecutionState.FINISHED

    return check_service_state


def not_condition(function: StartConditionCheckerFunction) -> StartConditionCheckerFunction:
    """
    Condition that returns opposite boolean value to the one returned by incoming function.
    :function: - the function to return opposite of.
    Returns StartConditionCheckerFunction.
    """

    def not_fun(ctx: Context, actor: Actor):
        return not function(ctx, actor)

    return not_fun


def aggregate_condition(
    aggregator: StartConditionCheckerAggregationFunction, *functions: StartConditionCheckerFunction
) -> StartConditionCheckerFunction:
    """
    Condition that returns aggregated boolean value from all booleans returned by incoming functions.
    :aggregator: - the function that accepts list of booleans and returns a single boolean.
    :*functions: - functions to aggregate.
    Returns StartConditionCheckerFunction.
    """

    def aggregation_fun(ctx: Context, actor: Actor):
        return aggregator([function(ctx, actor) for function in functions])

    return aggregation_fun


def all_condition(*functions: StartConditionCheckerFunction) -> StartConditionCheckerFunction:
    """
    Condition that returns True only if all incoming functions return True.
    :*functions: - functions to aggregate.
    Returns StartConditionCheckerFunction.
    """
    return aggregate_condition(all, *functions)


def any_condition(*functions: StartConditionCheckerFunction) -> StartConditionCheckerFunction:
    """
    Condition that returns True if any of incoming functions returns True.
    :*functions: - functions to aggregate.
    Returns StartConditionCheckerFunction.
    """
    return aggregate_condition(any, *functions)
