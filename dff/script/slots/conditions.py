"""
Conditions
---------------------------
Functions from this module allow you to condition graph transitions depending on slot values.
Combined with operators available in :py:mod:`~dff.script.conditions.std_conditions`,
like :py:func:`~dff.script.conditions.std_conditions.negation`,
they provide a feasible way of iterating the script graph depending on the status of slot values.

"""
from dff.script import Context
from dff.pipeline import Pipeline, StartConditionCheckerFunction, all_condition, any_condition

from .types import SLOT_STORAGE_KEY


def slot_extracted_condition(path: str) -> StartConditionCheckerFunction:
    def check_slot_state(ctx: Context, _: Pipeline) -> bool:
        state = ctx.framework_states.get(SLOT_STORAGE_KEY, {}).get(path)
        return state is not None

    return check_slot_state


def is_set_all(paths: list) -> StartConditionCheckerFunction:
    return all_condition(*[slot_extracted_condition(path) for path in paths])


def is_set_any(paths: list) -> StartConditionCheckerFunction:
    return any_condition(*[slot_extracted_condition(path) for path in paths])
