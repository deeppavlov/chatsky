"""
Conditions
---------------------------
Functions from this module allow you to condition graph transitions depending on slot values.
"""
from dff.script import Context
from dff.pipeline import Pipeline, StartConditionCheckerFunction, all_condition, any_condition

from .types import SLOT_STORAGE_KEY


def slot_extracted_condition(path: str) -> StartConditionCheckerFunction:
    def check_slot_state(ctx: Context, _: Pipeline) -> bool:
        state = ctx.framework_states.get(SLOT_STORAGE_KEY, {}).get(path)
        return state is not None

    return check_slot_state


def is_set_all(paths: list):
    cond = all_condition(*[slot_extracted_condition(path) for path in paths])
    return cond


def is_set_any(paths: list):
    cond = any_condition(*[slot_extracted_condition(path) for path in paths])
    return cond
