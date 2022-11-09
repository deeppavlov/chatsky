"""
Utils
---------------------------
This module is for general-purpose functions for df_slots.
"""
from typing import Dict, Callable, Any
from logging import getLogger
from functools import wraps

from df_engine.core import Context, Actor
from df_engine.core.actor import ActorStage

logger = getLogger(__name__)


SLOT_STORAGE_KEY = "slots"
FORM_STORAGE_KEY = "forms"


def requires_storage(
    warn_message: str = "Storage has not been registered.", storage_key: str = SLOT_STORAGE_KEY, return_val: Any = None
) -> Callable:
    def storage_decorator(func: Callable) -> Callable:
        @wraps(func)
        def storage_wrapper(ctx: Context, actor: Actor, *args, **kwargs) -> Any:
            if ctx.validation:
                return return_val

            if storage_key not in ctx.framework_states:
                logger.warning(warn_message)
                return return_val

            return func(ctx, actor, *args, **kwargs)

        return storage_wrapper

    return storage_decorator


def register_storage(actor: Actor, storage_key: str = SLOT_STORAGE_KEY, storage: Dict[str, str] = None) -> None:
    """
    Adds a callback for an actor to save a slot storage in the context. You can override the default dictionary storage
    with any dictionary-like structure.

    Parameters
    ----------

    actor: :py:class:`~Actor`
        DF engine actor.
    storage: Dict[str, str]
        Data structure to store slots. Any dictionary-like mapping can be passed.
    """
    if not storage:
        storage = dict()

    def register_storage_inner(ctx: Context, actor: Actor, *args, **kwargs) -> None:
        if storage_key in ctx.framework_states:
            return
        ctx.framework_states[storage_key] = storage
        return

    actor.handlers[ActorStage.CONTEXT_INIT] = actor.handlers.get(ActorStage.CONTEXT_INIT, []) + [register_storage_inner]
