"""
Conditions
---------------------------
Functions from this module allow you to condition graph transitions depending on slot values.
"""
from typing import Dict, List, Callable
from functools import partial

from pydantic import validate_arguments

from df_engine.core import Context, Actor

from .root import root_slot
from .utils import requires_storage


@validate_arguments
def is_set(slots: List[str], use_all: bool = True, use_any: bool = False) -> Callable:
    """
    Check, if any of the passed slots have been set.
    Any or all slot names from the list can be considered.

    Parameters
    ----------

    slots: List[str]
        List of slot names to extract.
        Names of slots inside groups should be prefixed with group names, separated by '/': profile/username.
    """
    if use_all == use_any:
        raise ValueError("Parameters `use_all` and `use_any` are mutually exclusive.")

    @requires_storage("Cannot check slot status: slot storage missing.", return_val=False)
    def is_set_inner(ctx: Context, actor: Actor) -> bool:
        slots_set = [root_slot.children[name].is_set()(ctx, actor) for name in slots]
        if use_all:
            return all(slots_set)
        if use_any:
            return any(slots_set)

    return is_set_inner


is_set_all = partial(is_set, use_all=True, use_any=False)
is_set_all.__doc__ = is_set.__doc__

is_set_any = partial(is_set, use_any=True, use_all=False)
is_set_any.__doc__ = is_set.__doc__


@validate_arguments
def set_like_mask(mask: Dict[str, bool]) -> Callable[[Context, Actor], bool]:
    """
    Check, if the state of one or more slots corresponds to a dict-based boolean mask.

    Parameters
    ----------

    mask: Dict[str, bool]
        Dictionary-based boolean mask. Keys are slot names, values are slot states.
        `True` for 'set', `False` for 'not set'.
    """

    def set_like_mask_inner(ctx: Context, actor: Actor) -> bool:
        slots = list(mask.keys())
        values = [root_slot.children[name].is_set()(ctx, actor) for name in slots]
        return list(mask.values()) == values

    return set_like_mask_inner
