"""
Handlers
---------------------------
This module is for general functions that can be used in processing, conditions, or responses.
"""
import logging
from typing import Any, Dict, Optional, List, Union

from dff.script import Context
from dff.pipeline import Pipeline

from .types import BaseSlot, GroupSlot, SLOT_STORAGE_KEY, root_slot as root

logger = logging.getLogger(__name__)


def extract(ctx: Context, pipeline: Pipeline, slots: Optional[List[str]] = None) -> List[Optional[Any]]:
    """
    Extract the specified slots and return the received values as a list.
    If the value of a particular slot cannot be extracted, None is included instead.
    If `slots` argument is not provided, all slots will be extracted and returned.

    :return: A list of extracted values.
        If a list of slot names has been passed,
        the list of values is guaranteed to be of the same length.
        Otherwise, the length equals the number of all non-child slots.

    :param ctx: Context.
    :param pipeline: Pipeline.
    :param slots: List of slot names to extract.
        Names of slots inside groups should be prefixed with group names, separated by '/': profile/username.

    """
    target_names = slots or [key for key in root.children.keys() if "/" not in key]

    storage = ctx.framework_states.get(SLOT_STORAGE_KEY)
    if storage is None or ctx.validation is True:
        logger.warning("Failed to extract slot values: storage missing.")
        return [None] * len(target_names)

    results = []
    for name in target_names:
        if name not in root.children:
            results.append(None)
            continue
        target_slot: BaseSlot = root.children.get(name)
        val = target_slot.extract_value(ctx, pipeline)
        if not target_slot.is_set()(ctx, pipeline):
            current_val = ctx.framework_states.get(SLOT_STORAGE_KEY, {})
            if isinstance(target_slot, GroupSlot):
                ctx.framework_states[SLOT_STORAGE_KEY] = {**current_val, **val}
            else:
                ctx.framework_states[SLOT_STORAGE_KEY] = {**current_val, **{name: val}}
        results.append(val)

    return results


def get_values(
    ctx: Context, pipeline: Pipeline, slots: Optional[List[str]] = None
) -> List[Dict[str, Union[str, None]]]:
    """
    Get values of the specified slots, assuming that they have been extracted beforehand.
    If slot argument is omitted, values of all slots will be returned.

    :return: A list of values.
        If a list of slot names has been passed,
        the list of values is guaranteed to be of the same length.
        Otherwise, the length equals the number of all non-child slots.

    :param ctx: Context
    :param pipeline: Pipeline.
    :param slots: List of slot names to extract.
        Names of slots inside groups should be prefixed with group names, separated by '/': profile/username.

    """
    target_names = slots or [key for key in root.children.keys() if "/" not in key]

    storage = ctx.framework_states.get(SLOT_STORAGE_KEY)
    if storage is None or ctx.validation is True:
        return [{key: None} for key in target_names]

    results = []
    for name in target_names:
        if name not in root.children:
            results.append(None)
        else:
            results.append(root.children[name].get_value()(ctx, pipeline))
    return results


def get_filled_template(template: str, ctx: Context, pipeline: Pipeline, slots: Optional[List[str]] = None) -> str:
    """
    Fill a template string with slot values.

    :param template: Template string.
    :param ctx: Context.
    :param pipeline: Pipeline.
    :param slots: List of slot names to extract.
        Names of slots inside groups should be prefixed with group names, separated by '/': profile/username.
    """
    filler_slots: Dict[str, BaseSlot]
    if slots:
        filler_slots = {key: value for key, value in root.children.items() if key in slots}
    else:
        filler_slots = {key: value for key, value in root.children.items() if "/" not in key}

    if not filler_slots:
        raise ValueError(
            "Given subset does not intersect with slots in root: {}".format(", ".join(slots) if slots else str(None))
        )

    for _, slot in filler_slots.items():
        template = slot.fill_template(template)(ctx, pipeline)

    return template


def unset(ctx: Context, pipeline: Pipeline, slots: Optional[List[str]] = None) -> None:
    """
    Expunge the target slot values from the context, so that they don't count as 'set' anymore.

    :param ctx: Context.
    :param pipeline: Pipeline.
    :param slots: List of slot names to extract.
        Names of slots inside groups should be prefixed with group names, separated by '/': profile/username.
    """
    if slots:
        target_names = [key for key in slots if key in root.children]
    else:
        target_names = [key for key in root.children.keys() if "/" not in key]

    if not target_names:
        logger.warning(
            "Given subset does not intersect with slots in root: {}".format(", ".join(slots) if slots else str(None))
        )
        return

    for name in target_names:
        root.children[name].unset_value()(ctx, pipeline)
    return
