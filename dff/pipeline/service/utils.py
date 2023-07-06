"""
Utility Functions
-----------------
The Utility Functions module contains several utility functions that are commonly used throughout the DFF.
These functions provide a variety of utility functionality.
"""
import asyncio
from typing import Callable, Any, Optional, Tuple, Mapping


async def wrap_sync_function_in_async(func: Callable, *args, **kwargs) -> Any:
    """
    Utility function, that wraps both functions and coroutines in coroutines.
    Invokes `func` if it is just a callable and awaits, if this is a coroutine.

    :param func: Callable to wrap.
    :param \\*args: Function args.
    :param \\**kwargs: Function kwargs.
    :return: What function returns.
    """
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def _get_attrs_with_updates(
    obj: object,
    drop_attrs: Optional[Tuple[str, ...]] = None,
    replace_attrs: Optional[Mapping[str, str]] = None,
    add_attrs: Optional[Mapping[str, Any]] = None,
) -> dict:
    """
    Advanced customizable version of built-in `__dict__` property.
    Sometimes during Pipeline construction `Services` (or `ServiceGroups`) should be rebuilt,
    e.g. in case of some fields overriding.
    This method can be customized to return a dict,
    that can be spread (** operator) and passed to Service or ServiceGroup constructor.
    Base dict is formed via `vars` built-in function. All "private" or "dunder" fields are omitted.

    :param drop_attrs: A tuple of key names that should be removed from the resulting dict.
    :param replace_attrs: A mapping that should be replaced in the resulting dict.
    :param add_attrs: A mapping that should be added to the resulting dict.
    :return: Resulting dict.
    """
    drop_attrs = () if drop_attrs is None else drop_attrs
    replace_attrs = {} if replace_attrs is None else dict(replace_attrs)
    add_attrs = {} if add_attrs is None else dict(add_attrs)
    result = {}
    for attribute in vars(obj):
        if not attribute.startswith("__") and attribute not in drop_attrs:
            if attribute in replace_attrs:
                result[replace_attrs[attribute]] = getattr(obj, attribute)
            else:
                result[attribute] = getattr(obj, attribute)
    result.update(add_attrs)
    return result


def collect_defined_constructor_parameters_to_dict(**kwargs: Any):
    """
    Function, that creates dict from non-`None` constructor parameters of pipeline component.
    It is used in overriding component parameters,
    when service handler or service group service is instance of Service or ServiceGroup (or dict).
    It accepts same named parameters as component constructor.

    :return: Dict, containing key-value pairs of these parameters, that are not `None`.
    """
    return dict([(key, value) for key, value in kwargs.items() if value is not None])
